from time import sleep

import polars as pl
from prefect import task

from app.services import db, tba
from app.services.tba import _TBAEndpoint
from app.types import SyncType
from app.utils.batch_accumulator import BatchAccumulator


@task(
    name="Sync Alliances",
    description="Sync FRC alliances and alliance teams from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_alliances(sync_type: SyncType = SyncType.FULL, batch_size: int = 50):
    accumulator = BatchAccumulator(batch_size=batch_size)

    event_keys = db.get_event_keys(sync_type=sync_type)
    etags = db.get_etags(_TBAEndpoint.ALLIANCES)
    valid_team_keys = db.get_team_keys()

    for idx, event_key in enumerate(event_keys, start=1):
        etag_key = _TBAEndpoint.ALLIANCES.build(event_key=event_key)
        result = tba.get_alliances(
            event_key=event_key,
            etag=etags.get(etag_key),
        )

        if result is None:
            sleep(0.5)
            continue

        alliances_df, alliance_teams_df, etag = result

        alliance_teams_df = alliance_teams_df.filter(
            pl.col("team_key").is_in(valid_team_keys)
        )

        accumulator.add_data("alliances", alliances_df)
        accumulator.add_data("alliance_teams", alliance_teams_df)
        if etag:
            accumulator.add_etag(etag_key, etag)

        if accumulator.should_flush(idx, len(event_keys)):
            if accumulator.get_data("alliances"):
                combined = pl.concat(accumulator.get_data("alliances"))
                db.upsert(
                    combined,
                    table_name="alliances",
                    conflict_key=["event_key", "name"],
                )
                accumulator.clear_data("alliances")

            if accumulator.get_data("alliance_teams"):
                combined = pl.concat(accumulator.get_data("alliance_teams"))
                db.upsert(
                    combined,
                    table_name="alliance_teams",
                    conflict_key=["event_key", "alliance_name", "team_key"],
                )
                accumulator.clear_data("alliance_teams")

            if accumulator.etag_updates:
                combined = pl.DataFrame(accumulator.etag_updates)
                db.upsert(
                    combined,
                    table_name="etags",
                    conflict_key=["endpoint"],
                )

                accumulator.clear_etags()

        sleep(0.5)

    if accumulator.has_data():
        if accumulator.get_data("alliances"):
            combined = pl.concat(accumulator.get_data("alliances"))
            db.upsert(
                combined,
                table_name="alliances",
                conflict_key=["event_key", "name"],
            )

        if accumulator.get_data("alliance_teams"):
            combined = pl.concat(accumulator.get_data("alliance_teams"))
            db.upsert(
                combined,
                table_name="alliance_teams",
                conflict_key=["event_key", "alliance_name", "team_key"],
            )

        if accumulator.etag_updates:
            combined = pl.DataFrame(accumulator.etag_updates)
            db.upsert(
                combined,
                table_name="etags",
                conflict_key=["endpoint"],
            )
