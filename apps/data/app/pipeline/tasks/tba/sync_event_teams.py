from time import sleep

import polars as pl
from prefect import get_run_logger, task
from pydantic import TypeAdapter

from app.models import ETag
from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint
from app.types import SyncType


@task(
    name="Sync Event Teams",
    description="Sync FRC event team participations from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_event_teams(sync_type: SyncType = SyncType.FULL):
    logger = get_run_logger()

    logger.info(
        f"Starting event teams sync from The Blue Alliance (sync_type={sync_type.value})"
    )

    tba = TBAService()
    db = DBService()

    event_teams_list: list[pl.DataFrame] = []
    etags_list: list[dict[str, str]] = []

    event_keys = db.get_event_keys(sync_type=sync_type)
    logger.info(f"Found {len(event_keys)} events to process")

    for event_key in event_keys:
        etag_key = _TBAEndpoint.EVENT_TEAMS.build(event_key=event_key)

        result = tba.get_event_teams(
            event_key=event_key,
            etag=db.get_etag(endpoint=etag_key),
        )

        if result is None:  # ETag cache hit
            logger.debug(f"Cache hit for event {event_key}")
            continue

        event_teams_df, etag = result

        logger.debug(f"Retrieved {len(event_teams_df)} teams for event {event_key}")
        event_teams_list.append(event_teams_df)

        if etag:
            etags_list.append({"endpoint": etag_key, "etag": etag})

        sleep(3.0)

    if event_teams_list:
        event_teams_df = pl.concat(event_teams_list)
        logger.info(f"Upserting {len(event_teams_df)} event teams to database")

        db.upsert(
            event_teams_df,
            table_name="event_teams",
            conflict_key=["event_key", "team_key"],
        )
        logger.info("Successfully synced event teams")
    else:
        logger.info("No new event team data to sync")

    if etags_list:
        TypeAdapter(list[ETag]).validate_python(etags_list)
        etags_df = pl.DataFrame(etags_list)

        db.upsert(
            etags_df,
            table_name="etags",
            conflict_key="endpoint",
        )
        logger.debug(f"Updated {len(etags_list)} ETag(s)")

    logger.info(
        f"Event teams sync completed successfully (sync_type={sync_type.value})"
    )
