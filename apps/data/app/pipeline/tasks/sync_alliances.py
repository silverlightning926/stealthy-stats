from time import sleep

from prefect import get_run_logger, task

from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint
from app.types import SyncType


@task(
    name="Sync Alliances",
    description="Sync FRC alliances and alliance teams from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_alliances(sync_type: SyncType = SyncType.FULL):
    logger = get_run_logger()

    logger.info(
        f"Starting alliances sync from The Blue Alliance (sync_type={sync_type.value})"
    )

    tba = TBAService()
    db = DBService()

    event_keys = db.get_event_keys(sync_type=sync_type)
    logger.info(f"Found {len(event_keys)} events to process")

    total_alliances = 0
    total_alliance_teams = 0

    for event_key in event_keys:
        etag_key = _TBAEndpoint.ALLIANCES.build(event_key=event_key)

        result = tba.get_alliances(
            event_key=event_key,
            etag=db.get_etag(endpoint=etag_key),
        )

        if result is None:  # ETag cache hit
            logger.debug(f"Cache hit for event {event_key}")
            continue

        event_alliances_df, event_alliance_teams_df, etag = result

        logger.debug(
            f"Retrieved {len(event_alliances_df)} alliances and {len(event_alliance_teams_df)} alliance teams for event {event_key}"
        )

        if not event_alliances_df.is_empty():
            db.upsert(
                event_alliances_df,
                table_name="alliances",
                conflict_key=["event_key", "name"],
            )
            total_alliances += len(event_alliances_df)
            logger.info(
                f"Upserted {len(event_alliances_df)} alliances for event {event_key}"
            )

        if not event_alliance_teams_df.is_empty():
            db.upsert(
                event_alliance_teams_df,
                table_name="alliance_teams",
                conflict_key=["event_key", "alliance_name", "team_key"],
            )
            total_alliance_teams += len(event_alliance_teams_df)
            logger.info(
                f"Upserted {len(event_alliance_teams_df)} alliance teams for event {event_key}"
            )

        if etag:
            db.upsert_etag(endpoint=etag_key, etag=etag)

        sleep(3.0)

    logger.info(f"Successfully synced {total_alliances} alliances")
    logger.info(f"Successfully synced {total_alliance_teams} alliance teams")

    logger.info(f"Alliances sync completed successfully (sync_type={sync_type.value})")
