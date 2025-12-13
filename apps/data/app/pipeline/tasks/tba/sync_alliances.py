from time import sleep

import polars as pl
from prefect import get_run_logger, task
from pydantic import TypeAdapter

from app.models import ETag
from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint


@task(
    name="Sync Alliances",
    description="Sync FRC alliances from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_alliances(active_only: bool = False):
    logger = get_run_logger()

    mode = "active events" if active_only else "all events"
    logger.info(f"Starting alliances sync from The Blue Alliance for {mode}")

    tba = TBAService()
    db = DBService()

    alliances: list[pl.DataFrame] = []

    etags: list[dict[str, str]] = []

    event_keys = db.get_event_keys(active_only=active_only)

    logger.info(f"Found {len(event_keys)} events to process")

    for event in event_keys:
        etag_key = _TBAEndpoint.ALLIANCES.build(event_key=event)

        result = tba.get_alliances(
            event_key=event,
            etag=db.get_etag(endpoint=etag_key),
        )

        if result is None:  # ETag Hit:
            logger.debug(f"Cache hit for event {event}")
            continue  # Skip to next loop iteration

        event_alliances, etag = result

        logger.debug(f"Retrieved {len(event_alliances)} alliances for event {event}")
        alliances.append(event_alliances)

        if etag:
            etags.append({"endpoint": etag_key, "etag": etag})

        sleep(3.0)

    if alliances:
        alliances_df = pl.concat(alliances)

        logger.info(f"Upserting {len(alliances_df)} alliances to database")

        db.upsert(
            alliances_df,
            table_name="alliances",
            conflict_key=["event_key", "name"],
        )

        logger.info("Successfully synced alliances")
    else:
        logger.info("No new alliance data to sync")

    if etags:
        TypeAdapter(list[ETag]).validate_python(etags)

        etags_df = pl.DataFrame(etags)

        db.upsert(
            etags_df,
            table_name="etags",
            conflict_key="endpoint",
        )

        logger.debug(f"Updated {len(etags)} ETag(s)")

    logger.info(f"Alliances sync completed successfully for {mode}")
