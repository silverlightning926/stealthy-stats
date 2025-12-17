from time import sleep

import polars as pl
from prefect import get_run_logger, task

from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint
from app.types import SyncType


@task(
    name="Sync Event Teams",
    description="Sync FRC event team participations from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_event_teams(sync_type: SyncType = SyncType.FULL):
    logger = get_run_logger()

    logger.info(
        f"Starting event teams sync from The Blue Alliance (sync_type={sync_type.value})"
    )

    tba = TBAService()
    db = DBService()

    event_keys = db.get_event_keys(sync_type=sync_type)
    logger.info(f"Found {len(event_keys)} events to process")

    total_event_teams = 0

    for event_key in event_keys:
        etag_key = _TBAEndpoint.EVENT_TEAMS.build(event_key=event_key)

        result = tba.get_event_teams(
            event_key=event_key,
            etag=db.get_etag(endpoint=etag_key),
        )

        if result is None:  # ETag cache hit
            logger.debug(f"Cache hit for event {event_key}")
            continue

        event_teams_df, etag = result

        logger.debug(f"Retrieved {len(event_teams_df)} teams for event {event_key}")

        if not event_teams_df.is_empty():
            original_length = len(event_teams_df)
            event_teams_df = event_teams_df.filter(
                pl.col("team_key").is_in(db.get_team_keys())
            )

            removed_count = original_length - len(event_teams_df)
            if removed_count > 0:
                logger.debug(
                    f"Removed {removed_count} ghost teams for event {event_key}"
                )

            if not event_teams_df.is_empty():
                db.upsert(
                    event_teams_df,
                    table_name="event_teams",
                    conflict_key=["event_key", "team_key"],
                )
                total_event_teams += len(event_teams_df)
                logger.info(
                    f"Upserted {len(event_teams_df)} event teams for event {event_key}"
                )

        if etag:
            db.upsert_etag(endpoint=etag_key, etag=etag)

        sleep(3.0)

    logger.info(f"Successfully synced {total_event_teams} event teams")

    logger.info(
        f"Event teams sync completed successfully (sync_type={sync_type.value})"
    )
