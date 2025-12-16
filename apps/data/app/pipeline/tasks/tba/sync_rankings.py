from time import sleep

import polars as pl
from prefect import get_run_logger, task
from pydantic import TypeAdapter

from app.models import ETag
from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint
from app.types import SyncType


@task(
    name="Sync Rankings",
    description="Sync FRC rankings and ranking event info from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_rankings(sync_type: SyncType = SyncType.FULL):
    logger = get_run_logger()

    logger.info(
        f"Starting rankings sync from The Blue Alliance (sync_type={sync_type.value})"
    )

    tba = TBAService()
    db = DBService()

    rankings_list: list[pl.DataFrame] = []
    ranking_event_infos_list: list[pl.DataFrame] = []
    etags_list: list[dict[str, str]] = []

    event_keys = db.get_event_keys(sync_type=sync_type)
    logger.info(f"Found {len(event_keys)} events to process")

    for event_key in event_keys:
        etag_key = _TBAEndpoint.RANKINGS.build(event_key=event_key)

        result = tba.get_rankings(
            event_key=event_key,
            etag=db.get_etag(endpoint=etag_key),
        )

        if result is None:  # ETag cache hit
            logger.debug(f"Cache hit for event {event_key}")
            continue

        event_rankings_df, event_ranking_event_info_df, etag = result

        logger.debug(
            f"Retrieved {len(event_rankings_df)} rankings and {len(event_ranking_event_info_df)} ranking event info record for event {event_key}"
        )
        rankings_list.append(event_rankings_df)
        ranking_event_infos_list.append(event_ranking_event_info_df)

        if etag:
            etags_list.append({"endpoint": etag_key, "etag": etag})

        sleep(3.0)

    if ranking_event_infos_list:
        ranking_event_infos_df = pl.concat(ranking_event_infos_list)
        logger.info(
            f"Upserting {len(ranking_event_infos_df)} ranking event info records to database"
        )

        db.upsert(
            ranking_event_infos_df,
            table_name="ranking_event_infos",
            conflict_key="event_key",
        )
        logger.info("Successfully synced ranking event info")
    else:
        logger.info("No new ranking event info data to sync")

    if rankings_list:
        rankings_df = pl.concat(rankings_list)
        logger.info(f"Upserting {len(rankings_df)} rankings to database")

        db.upsert(
            rankings_df,
            table_name="rankings",
            conflict_key=["event_key", "team_key"],
        )
        logger.info("Successfully synced rankings")
    else:
        logger.info("No new ranking data to sync")

    if etags_list:
        TypeAdapter(list[ETag]).validate_python(etags_list)
        etags_df = pl.DataFrame(etags_list)

        db.upsert(
            etags_df,
            table_name="etags",
            conflict_key="endpoint",
        )
        logger.debug(f"Updated {len(etags_list)} ETag(s)")

    logger.info(f"Rankings sync completed successfully (sync_type={sync_type.value})")
