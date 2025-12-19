from prefect import flow
from prefect.logging import get_run_logger

from app.pipeline.tasks import (
    sync_alliances,
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
    logger.info("Starting year sync flow")

    logger.info("Step 1/4: Syncing events")
    sync_events(sync_type=SyncType.YEAR)

    logger.info("Step 2/4: Syncing matches")
    sync_matches(sync_type=SyncType.YEAR)

    logger.info("Step 3/4: Syncing rankings")
    sync_rankings(sync_type=SyncType.YEAR)

    logger.info("Step 4/4: Syncing alliances")
    sync_alliances(sync_type=SyncType.YEAR)

    logger.info("Year sync flow completed successfully")
