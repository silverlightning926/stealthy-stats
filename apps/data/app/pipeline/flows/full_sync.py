from prefect import flow

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
    sync_teams()
    sync_events()
    sync_matches(active_only=False)
    sync_rankings(active_only=False)
    sync_alliances(active_only=False)
