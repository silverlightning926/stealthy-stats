from prefect import flow, get_run_logger

from app.pipeline.tasks.tba import (
    sync_alliances,
    sync_events,
    sync_matches,
    sync_rankings,
    sync_teams,
)


@flow(
    name="Full Sync",
    description="Comprehensive data sync that syncs any new FRC data and calculates analytics",
    retries=2,
    retry_delay_seconds=30,
)
def full_sync():
    logger = get_run_logger()

    logger.info("Starting full sync of all FRC data")

    try:
        logger.info("Step 1/5: Syncing teams")
        sync_teams()

        logger.info("Step 2/5: Syncing events")
        sync_events()

        logger.info("Step 3/5: Syncing matches")
        sync_matches(active_only=False)

        logger.info("Step 4/5: Syncing rankings")
        sync_rankings(active_only=False)

        logger.info("Step 5/5: Syncing alliances")
        sync_alliances(active_only=False)

        logger.info("Full sync completed successfully")

    except Exception as e:
        logger.error(f"Full sync failed with error: {e}")
        raise
