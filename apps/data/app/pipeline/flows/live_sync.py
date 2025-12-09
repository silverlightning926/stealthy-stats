from prefect import flow

from app.pipeline.tasks.tba import sync_matches


@flow(
    name="Live Sync",
    description="Quick and live sync that runs often to keep up with live events",
    retries=2,
    retry_delay_seconds=30,
)
def live_sync():
    sync_matches(active_only=True)
