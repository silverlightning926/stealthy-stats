from time import sleep

import polars as pl
from prefect import get_run_logger, task
from pydantic import TypeAdapter

from app.models import ETag
from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint


@task(
    name="Sync Matches",
    description="Sync FRC matches from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_matches(active_only: bool = False):
    logger = get_run_logger()

    mode = "active events" if active_only else "all events"
    logger.info(f"Starting match sync from The Blue Alliance for {mode}")

    tba = TBAService()
    db = DBService()

    matches: list[pl.DataFrame] = []
    match_alliances: list[pl.DataFrame] = []

    etags: list[dict[str, str]] = []

    event_keys = db.get_event_keys(active_only=active_only)

    logger.info(f"Found {len(event_keys)} events to process")

    for event in event_keys:
        etag_key = _TBAEndpoint.MATCHES.build(event_key=event)

        result = tba.get_matches(
            event_key=event,
            etag=db.get_etag(endpoint=etag_key),
        )

        if result is None:  # ETag Hit:
            logger.debug(f"Cache hit for event {event}")
            continue  # Skip to next loop iteration

        event_matches, event_match_alliances, etag = result

        logger.debug(f"Retrieved {len(event_matches)} matches for event {event}")
        matches.append(event_matches)
        match_alliances.append(event_match_alliances)

        if etag:
            etags.append({"endpoint": etag_key, "etag": etag})

        sleep(3.0)

    if match_alliances:
        match_alliances_df = pl.concat(match_alliances)

        logger.info(f"Upserting {len(match_alliances_df)} match alliances to database")

        db.upsert(
            match_alliances_df,
            table_name="match_alliances",
            conflict_key=["match_key", "alliance_color"],
        )

        logger.info("Successfully synced match alliances")
    else:
        logger.info("No new match alliance data to sync")

    if matches:
        matches_df = pl.concat(matches)

        logger.info(f"Upserting {len(matches_df)} matches to database")

        db.upsert(
            matches_df,
            table_name="matches",
            conflict_key="key",
        )

        logger.info("Successfully synced matches")
    else:
        logger.info("No new match data to sync")

    if etags:
        TypeAdapter(list[ETag]).validate_python(etags)

        etags_df = pl.DataFrame(etags)

        db.upsert(
            etags_df,
            table_name="etags",
            conflict_key="endpoint",
        )

        logger.debug(f"Updated {len(etags)} ETag(s)")

    logger.info(f"Match sync completed successfully for {mode}")
