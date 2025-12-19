from prefect import flow
from prefect.logging import get_run_logger

from app.pipeline.tasks import (
    sync_alliances,
    sync_events,
    sync_matches,
    sync_rankings,
    sync_teams,
)
from app.types import SyncType


@flow(
    name="Full Sync",
    description="Comprehensive data sync that syncs any new FRC data and calculates analytics",
    retries=2,
    retry_delay_seconds=30,
)
def full_sync():
    logger = get_run_logger()
    logger.info("Starting full sync flow")

    logger.info("Step 1/5: Syncing teams")
    sync_teams()

    logger.info("Step 2/5: Syncing events")
    sync_events(sync_type=SyncType.FULL)

    logger.info("Step 3/5: Syncing matches")
    sync_matches(sync_type=SyncType.FULL)

    logger.info("Step 4/5: Syncing rankings")
    sync_rankings(sync_type=SyncType.FULL)

    logger.info("Step 5/5: Syncing alliances")
    sync_alliances(sync_type=SyncType.FULL)

    logger.info("Full sync flow completed successfully")
