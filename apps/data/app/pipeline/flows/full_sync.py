from prefect import flow

from app.pipeline.tasks.tba import sync_districts, sync_events, sync_teams


@flow(
    name="Full Sync",
    description="Comprehensive data sync that syncs any new FRC data and calculates analytics",
    retries=2,
    retry_delay_seconds=30,
)
def full_sync():
    sync_teams()
    sync_districts()
    sync_events()
