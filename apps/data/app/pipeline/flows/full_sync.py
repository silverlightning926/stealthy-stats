from prefect import flow
from prefect.logging import get_run_logger

from app.pipeline.tasks import (
    sync_alliances,
    sync_event_teams,
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

    logger.info("Step 1/6: Syncing teams")
    sync_teams()

    logger.info("Step 2/6: Syncing events")
    sync_events(sync_type=SyncType.FULL)

    logger.info("Step 3/6: Syncing event teams")
    sync_event_teams(sync_type=SyncType.FULL)

    logger.info("Step 4/6: Syncing matches")
    sync_matches(sync_type=SyncType.FULL)

    logger.info("Step 5/6: Syncing rankings")
    sync_rankings(sync_type=SyncType.FULL)

    logger.info("Step 6/6: Syncing alliances")
    sync_alliances(sync_type=SyncType.FULL)

    logger.info("Full sync flow completed successfully")
