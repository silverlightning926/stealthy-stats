from time import sleep

import polars as pl
from prefect import task

from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint
from app.types import SyncType
from app.utils.batch_accumulator import BatchAccumulator


@task(
    name="Sync Rankings",
    description="Sync FRC rankings and ranking event info from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_rankings(sync_type: SyncType = SyncType.FULL, batch_size: int = 50):
    tba = TBAService()
    db = DBService()
    accumulator = BatchAccumulator(batch_size=batch_size)

    event_keys = db.get_event_keys(sync_type=sync_type)
    etags = db.get_etags(_TBAEndpoint.RANKINGS)
    valid_team_keys = db.get_team_keys()

    for idx, event_key in enumerate(event_keys, start=1):
        etag_key = _TBAEndpoint.RANKINGS.build(event_key=event_key)
        result = tba.get_rankings(
            event_key=event_key,
            etag=etags.get(etag_key),
        )

        if result is None:
            sleep(0.5)
            continue

        rankings_df, ranking_event_info_df, etag = result

        rankings_df = rankings_df.filter(pl.col("team_key").is_in(valid_team_keys))

        accumulator.add_data("rankings", rankings_df)
        accumulator.add_data("ranking_event_infos", ranking_event_info_df)
        if etag:
            accumulator.add_etag(etag_key, etag)

        if accumulator.should_flush(idx, len(event_keys)):
            if accumulator.get_data("ranking_event_infos"):
                combined = pl.concat(accumulator.get_data("ranking_event_infos"))
                db.upsert(
                    combined,
                    table_name="ranking_event_infos",
                    conflict_key="event_key",
                )
                accumulator.clear_data("ranking_event_infos")

            if accumulator.get_data("rankings"):
                combined = pl.concat(accumulator.get_data("rankings"))
                db.upsert(
                    combined,
                    table_name="rankings",
                    conflict_key=["event_key", "team_key"],
                )
                accumulator.clear_data("rankings")

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
        if accumulator.get_data("ranking_event_infos"):
            combined = pl.concat(accumulator.get_data("ranking_event_infos"))
            db.upsert(
                combined,
                table_name="ranking_event_infos",
                conflict_key="event_key",
            )

        if accumulator.get_data("rankings"):
            combined = pl.concat(accumulator.get_data("rankings"))
            db.upsert(
                combined,
                table_name="rankings",
                conflict_key=["event_key", "team_key"],
            )

        if accumulator.etag_updates:
            combined = pl.DataFrame(accumulator.etag_updates)
            db.upsert(
                combined,
                table_name="etags",
                conflict_key=["endpoint"],
            )
