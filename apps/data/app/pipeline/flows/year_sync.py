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
    name="Year Sync",
    description="Live data sync that syncs FRC data for the current year and calculates analytics",
    retries=2,
    retry_delay_seconds=30,
)
def year_sync():
    logger = get_run_logger()
    logger.info("Starting year sync flow")

    logger.info("Step 1/6: Syncing teams")
    sync_teams()

    logger.info("Step 2/6: Syncing events")
    sync_events(sync_type=SyncType.YEAR)

    logger.info("Step 3/6: Syncing event teams")
    sync_event_teams(sync_type=SyncType.YEAR)

    logger.info("Step 4/6: Syncing matches")
    sync_matches(sync_type=SyncType.YEAR)

    logger.info("Step 5/6: Syncing rankings")
    sync_rankings(sync_type=SyncType.YEAR)

    logger.info("Step 6/6: Syncing alliances")
    sync_alliances(sync_type=SyncType.YEAR)

    logger.info("Year sync flow completed successfully")
