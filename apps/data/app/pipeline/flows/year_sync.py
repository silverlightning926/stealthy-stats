from prefect import flow, get_run_logger

from app.pipeline.tasks.tba import (
    sync_alliances,
    sync_event_teams,
    sync_events,
    sync_matches,
    sync_rankings,
)
from app.types import SyncType


@flow(
    name="Year Sync",
    description="Live data sync that syncs FRC data for the current year and calculates analytics",
    retries=2,
    retry_delay_seconds=30,
)
def year_sync():
    logger = get_run_logger()

    logger.info("Starting year sync")

    try:
        logger.info("Step 1/5: Syncing events")
        sync_events(sync_type=SyncType.YEAR)

        logger.info("Step 2/5: Syncing event teams")
        sync_event_teams(sync_type=SyncType.YEAR)

        logger.info("Step 3/5: Syncing matches")
        sync_matches(sync_type=SyncType.YEAR)

        logger.info("Step 4/5: Syncing rankings")
        sync_rankings(sync_type=SyncType.YEAR)

        logger.info("Step 5/5: Syncing alliances")
        sync_alliances(sync_type=SyncType.YEAR)

        logger.info("Year sync completed successfully")

    except Exception as e:
        logger.error(f"Year sync failed with error: {e}")
        raise
