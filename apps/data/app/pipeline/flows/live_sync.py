from prefect import flow, get_run_logger

from app.pipeline.tasks.tba import sync_alliances, sync_matches, sync_rankings
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

        active_events = db.get_event_keys(active_only=True)
        if not active_events:
            logger.info("No active events found - skipping live sync")
            return

        logger.info(
            f"Found {len(active_events)} active event(s) - proceeding with live sync"
        )

        logger.info("Step 1/3: Syncing matches for active events")
        sync_matches(active_only=True)

        logger.info("Step 2/3: Syncing rankings for active events")
        sync_rankings(active_only=True)

        logger.info("Step 3/3: Syncing alliances for active events")
        sync_alliances(active_only=True)

        logger.info("Live sync completed successfully")

    except Exception as e:
        logger.error(f"Live sync failed with error: {e}")
        raise
