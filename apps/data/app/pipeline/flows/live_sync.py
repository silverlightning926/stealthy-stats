from prefect import flow

from app.pipeline.tasks.tba import sync_matches, sync_rankings
from app.services import DBService


@flow(
    name="Live Sync",
    description="Quick and live sync that runs often to keep up with live events",
    retries=2,
    retry_delay_seconds=30,
)
def live_sync():
    db = DBService()

    if not db.get_event_keys(active_only=True):
        return

    sync_matches(active_only=True)
    sync_rankings(active_only=True)
