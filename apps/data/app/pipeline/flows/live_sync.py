from prefect import flow

from app.pipeline.tasks import (
    sync_alliances,
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
    active_events = db.get_event_keys(sync_type=SyncType.LIVE)
    if not active_events:
        return

    sync_matches(sync_type=SyncType.LIVE)

    sync_rankings(sync_type=SyncType.LIVE)

    sync_alliances(sync_type=SyncType.LIVE)
