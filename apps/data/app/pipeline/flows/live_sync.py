from prefect import flow
from prefect.logging import get_run_logger

from app.pipeline.tasks import (
    sync_alliances,
    sync_event_teams,
    sync_matches,
    sync_rankings,
)
from app.services import db
from app.types import SyncType


@flow(
    name="Live Sync",
    description="Quick and live sync that runs often to keep up with live events",
    retries=2,
    retry_delay_seconds=30,
)
def live_sync():
    logger = get_run_logger()
    logger.info("Starting live sync flow")

    active_events = db.get_event_keys(sync_type=SyncType.LIVE)
    if not active_events:
        logger.info("No active events found, skipping sync")
        return

    logger.info(f"Found {len(active_events)} active events")

    logger.info("Step 1/4: Syncing Event Teams")
    sync_event_teams(sync_type=SyncType.LIVE)

    logger.info("Step 2/4: Syncing matches")
    sync_matches(sync_type=SyncType.LIVE)

    logger.info("Step 3/4: Syncing rankings")
    sync_rankings(sync_type=SyncType.LIVE)

    logger.info("Step 4/4: Syncing alliances")
    sync_alliances(sync_type=SyncType.LIVE)

    logger.info("Live sync flow completed successfully")
