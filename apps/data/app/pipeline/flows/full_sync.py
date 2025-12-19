from prefect import flow

from app.pipeline.tasks import (
    sync_alliances,
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
    sync_teams()

    sync_events(sync_type=SyncType.FULL)

    sync_matches(sync_type=SyncType.FULL)

    sync_rankings(sync_type=SyncType.FULL)

    sync_alliances(sync_type=SyncType.FULL)
