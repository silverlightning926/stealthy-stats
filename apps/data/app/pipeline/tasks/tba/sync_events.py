from datetime import datetime
from time import sleep

import polars as pl
from prefect import get_run_logger, task
from pydantic import TypeAdapter

from app.models import ETag
from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint


@task(
    name="Sync Events",
    description="Sync FRC events and districts from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_events():
    logger = get_run_logger()
    logger.info("Starting event sync from The Blue Alliance")

    tba = TBAService()
    db = DBService()

    events_list: list[pl.DataFrame] = []
    event_districts_list: list[pl.DataFrame] = []
    etags_list: list[dict[str, str]] = []

    start_year = 1992
    end_year = datetime.now().year
    logger.info(f"Syncing events from {start_year} to {end_year}")

    for year in range(start_year, end_year + 1):
        if year == 2021:
            logger.debug("Skipping year 2021 (no competition season)")
            continue

        etag_key = _TBAEndpoint.EVENTS.build(year=str(year))

        result = tba.get_events(
            year=year,
            etag=db.get_etag(endpoint=etag_key),
        )

        if result is None:  # ETag cache hit
            logger.debug(f"Cache hit for year {year}")
            continue

        year_events_df, year_event_districts_df, etag = result

        logger.debug(
            f"Retrieved {len(year_events_df)} events and {len(year_event_districts_df)} districts for year {year}"
        )
        events_list.append(year_events_df)
        event_districts_list.append(year_event_districts_df)

        if etag:
            etags_list.append({"endpoint": etag_key, "etag": etag})

        sleep(1.5)

    if event_districts_list:
        event_districts_df = pl.concat(event_districts_list)
        logger.info(f"Upserting {len(event_districts_df)} districts to database")

        db.upsert(
            event_districts_df,
            table_name="event_districts",
            conflict_key="key",
        )
        logger.info("Successfully synced event districts")
    else:
        logger.info("No new event district data to sync")

    if events_list:
        events_df = pl.concat(events_list)
        logger.info(f"Upserting {len(events_df)} events to database")

        db.upsert(
            events_df,
            table_name="events",
            conflict_key="key",
        )
        logger.info("Successfully synced events")
    else:
        logger.info("No new event data to sync")

    if etags_list:
        TypeAdapter(list[ETag]).validate_python(etags_list)
        etags_df = pl.DataFrame(etags_list)

        db.upsert(
            etags_df,
            table_name="etags",
            conflict_key="endpoint",
        )
        logger.debug(f"Updated {len(etags_list)} ETag(s)")

    logger.info("Event sync completed successfully")
