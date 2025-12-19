from time import sleep

import polars as pl
from prefect import task
from prefect.logging import get_run_logger

from app.services import db, tba
from app.services.tba import _TBAEndpoint
from app.types import SyncType
from app.utils.batch_accumulator import BatchAccumulator


@task(
    name="Sync Matches",
    description="Sync FRC matches, match alliances, and match alliance teams from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_matches(sync_type: SyncType = SyncType.FULL, batch_size: int = 25):
    logger = get_run_logger()
    logger.info(
        f"Starting match sync with sync_type={sync_type.value}, batch_size={batch_size}"
    )

    accumulator = BatchAccumulator(batch_size=batch_size)

    event_keys = db.get_event_keys(sync_type=sync_type)
    etags = db.get_etags(_TBAEndpoint.MATCHES)
    valid_team_keys = db.get_team_keys()

    logger.info(f"Syncing matches for {len(event_keys)} events")

    for idx, event_key in enumerate(event_keys, start=1):
        etag_key = _TBAEndpoint.MATCHES.build(event_key=event_key)
        result = tba.get_matches(
            event_key=event_key,
            etag=etags.get(etag_key),
        )

        if result is None:
            logger.debug(
                f"[{idx}/{len(event_keys)}] No updates for {event_key} (cached)"
            )
            sleep(0.5)
            continue

        matches_df, match_alliances_df, match_alliance_teams_df, etag = result
        logger.debug(
            f"[{idx}/{len(event_keys)}] Retrieved {len(matches_df)} matches, {len(match_alliances_df)} match alliances, {len(match_alliance_teams_df)} match alliance teams for {event_key}"
        )

        match_alliance_teams_df = match_alliance_teams_df.filter(
            pl.col("team_key").is_in(valid_team_keys)
        )

        accumulator.add_data("matches", matches_df)
        accumulator.add_data("match_alliances", match_alliances_df)
        accumulator.add_data("match_alliance_teams", match_alliance_teams_df)
        if etag:
            accumulator.add_etag(etag_key, etag)

        if accumulator.should_flush(idx, len(event_keys)):
            logger.info(f"[{idx}/{len(event_keys)}] Flushing batch to database")

            if accumulator.get_data("matches"):
                combined = pl.concat(accumulator.get_data("matches"))
                db.upsert(combined, table_name="matches", conflict_key="key")
                accumulator.clear_data("matches")

            if accumulator.get_data("match_alliances"):
                combined = pl.concat(accumulator.get_data("match_alliances"))
                db.upsert(
                    combined,
                    table_name="match_alliances",
                    conflict_key=["match_key", "alliance_color"],
                )
                accumulator.clear_data("match_alliances")

            if accumulator.get_data("match_alliance_teams"):
                combined = pl.concat(accumulator.get_data("match_alliance_teams"))
                db.upsert(
                    combined,
                    table_name="match_alliance_teams",
                    conflict_key=["match_key", "alliance_color", "team_key"],
                )
                accumulator.clear_data("match_alliance_teams")

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
        logger.info("Flushing final batch to database")

        if accumulator.get_data("matches"):
            combined = pl.concat(accumulator.get_data("matches"))
            db.upsert(combined, table_name="matches", conflict_key="key")

        if accumulator.get_data("match_alliances"):
            combined = pl.concat(accumulator.get_data("match_alliances"))
            db.upsert(
                combined,
                table_name="match_alliances",
                conflict_key=["match_key", "alliance_color"],
            )

        if accumulator.get_data("match_alliance_teams"):
            combined = pl.concat(accumulator.get_data("match_alliance_teams"))
            db.upsert(
                combined,
                table_name="match_alliance_teams",
                conflict_key=["match_key", "alliance_color", "team_key"],
            )

        if accumulator.etag_updates:
            combined = pl.DataFrame(accumulator.etag_updates)
            db.upsert(
                combined,
                table_name="etags",
                conflict_key=["endpoint"],
            )

    logger.info("Match sync completed successfully")
