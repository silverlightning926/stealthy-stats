from time import sleep

import polars as pl
from prefect import get_run_logger, task
from pydantic import TypeAdapter

from app.models import ETag
from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint


@task(
    name="Sync Rankings",
    description="Sync FRC rankings from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_rankings(active_only: bool = False):
    logger = get_run_logger()

    mode = "active events" if active_only else "all events"
    logger.info(f"Starting rankings sync from The Blue Alliance for {mode}")

    tba = TBAService()
    db = DBService()

    rankings: list[pl.DataFrame] = []
    ranking_infos: list[pl.DataFrame] = []

    etags: list[dict[str, str]] = []

    event_keys = db.get_event_keys(active_only=active_only)

    logger.info(f"Found {len(event_keys)} events to process")

    for event in event_keys:
        etag_key = _TBAEndpoint.RANKINGS.build(event_key=event)

        result = tba.get_rankings(
            event_key=event,
            etag=db.get_etag(endpoint=etag_key),
        )

        if result is None:  # ETag Hit:
            logger.debug(f"Cache hit for event {event}")
            continue  # Skip to next loop iteration

        event_rankings, event_rankings_info, etag = result

        logger.debug(f"Retrieved {len(event_rankings)} rankings for event {event}")
        rankings.append(event_rankings)
        ranking_infos.append(event_rankings_info)

        if etag:
            etags.append({"endpoint": etag_key, "etag": etag})

        sleep(3.0)

    if ranking_infos:
        ranking_infos_df = pl.concat(ranking_infos)

        logger.info(
            f"Upserting {len(ranking_infos_df)} ranking info records to database"
        )

        db.upsert(
            ranking_infos_df,
            table_name="event_ranking_info",
            conflict_key="event_key",
        )

        logger.info("Successfully synced ranking info")
    else:
        logger.info("No new ranking info data to sync")

    if rankings:
        rankings_df = pl.concat(rankings)

        logger.info(f"Upserting {len(rankings_df)} rankings to database")

        db.upsert(
            rankings_df,
            table_name="rankings",
            conflict_key=["event_key", "team_key"],
        )

        logger.info("Successfully synced rankings")
    else:
        logger.info("No new ranking data to sync")

    if etags:
        TypeAdapter(list[ETag]).validate_python(etags)

        etags_df = pl.DataFrame(etags)

        db.upsert(
            etags_df,
            table_name="etags",
            conflict_key="endpoint",
        )

        logger.debug(f"Updated {len(etags)} ETag(s)")

    logger.info(f"Rankings sync completed successfully for {mode}")
