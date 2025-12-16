from prefect import flow, get_run_logger

from app.pipeline.tasks.tba import (
    sync_alliances,
    sync_event_teams,
    sync_matches,
    sync_rankings,
)
from app.services import DBService


@flow(
    name="Live Sync",
    description="Quick and live sync that runs often to keep up with live events",
    retries=2,
    retry_delay_seconds=30,
)
def live_sync():
    logger = get_run_logger()

    logger.info("Starting live sync for active events")

    try:
        db = DBService()

        active_events = db.get_event_keys(filter="active")
        if not active_events:
            logger.info("No active events found - skipping live sync")
            return

        logger.info(
            f"Found {len(active_events)} active event(s) - proceeding with live sync"
        )

        logger.info("Step 1/4: Syncing event teams for active events")
        sync_event_teams(event_filter="active")

        logger.info("Step 2/4: Syncing matches for active events")
        sync_matches(event_filter="active")

        logger.info("Step 3/4: Syncing rankings for active events")
        sync_rankings(event_filter="active")

        logger.info("Step 4/4: Syncing alliances for active events")
        sync_alliances(event_filter="active")

        logger.info("Live sync completed successfully")

    except Exception as e:
        logger.error(f"Live sync failed with error: {e}")
        raise
