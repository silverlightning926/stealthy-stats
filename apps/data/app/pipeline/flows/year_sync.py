from prefect import flow

from app.pipeline.tasks import (
    sync_alliances,
    sync_events,
    sync_matches,
    sync_rankings,
)
from app.types import SyncType


@flow(
    name="Year Sync",
    description="Live data sync that syncs FRC data for the current year and calculates analytics",
    retries=2,
    retry_delay_seconds=30,
)
def year_sync():
    sync_events(sync_type=SyncType.YEAR)

    sync_matches(sync_type=SyncType.YEAR)

    sync_rankings(sync_type=SyncType.YEAR)

    sync_alliances(sync_type=SyncType.YEAR)
