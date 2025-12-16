from time import sleep

import polars as pl
from prefect import get_run_logger, task
from pydantic import TypeAdapter

from app.models import ETag
from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint
from app.types import EventFilter


@task(
    name="Sync Alliances",
    description="Sync FRC alliances and alliance teams from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_alliances(event_filter: EventFilter = "all", current_year: bool = False):
    logger = get_run_logger()

    logger.info(
        f"Starting alliances sync from The Blue Alliance (event_filter={event_filter}, current_year={current_year})"
    )

    tba = TBAService()
    db = DBService()

    alliances_list: list[pl.DataFrame] = []
    alliance_teams_list: list[pl.DataFrame] = []
    etags_list: list[dict[str, str]] = []

    event_keys = db.get_event_keys(filter=event_filter, current_year=current_year)
    logger.info(f"Found {len(event_keys)} events to process")

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
        alliances_list.append(event_alliances_df)
        alliance_teams_list.append(event_alliance_teams_df)

        if etag:
            etags_list.append({"endpoint": etag_key, "etag": etag})

        sleep(3.0)

    if alliances_list:
        alliances_df = pl.concat(alliances_list)
        logger.info(f"Upserting {len(alliances_df)} alliances to database")

        db.upsert(
            alliances_df,
            table_name="alliances",
            conflict_key=["event_key", "name"],
        )
        logger.info("Successfully synced alliances")
    else:
        logger.info("No new alliance data to sync")

    if alliance_teams_list:
        alliance_teams_df = pl.concat(alliance_teams_list)
        logger.info(f"Upserting {len(alliance_teams_df)} alliance teams to database")

        db.upsert(
            alliance_teams_df,
            table_name="alliance_teams",
            conflict_key=["event_key", "alliance_name", "team_key"],
        )
        logger.info("Successfully synced alliance teams")
    else:
        logger.info("No new alliance team data to sync")

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
        f"Alliances sync completed successfully (event_filter={event_filter}, current_year={current_year})"
    )
