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

    logger.info("Starting event and district sync from The Blue Alliance")

    tba = TBAService()
    db = DBService()

    events: list[pl.DataFrame] = []
    districts: list[pl.DataFrame] = []

    etags: list[dict[str, str]] = []

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

        if result is None:  # ETag Hit:
            logger.debug(f"Cache hit for year {year}")
            continue  # Skip to next loop iteration

        year_events, year_districts, etag = result

        logger.debug(
            f"Retrieved {len(year_events)} events and {len(year_districts)} districts for year {year}"
        )
        events.append(year_events)
        districts.append(year_districts)

        if etag:
            etags.append({"endpoint": etag_key, "etag": etag})

        sleep(1.5)

    if districts:
        districts_df = pl.concat(districts)

        logger.info(f"Upserting {len(districts_df)} districts to database")

        db.upsert(
            districts_df,
            table_name="districts",
            conflict_key="key",
        )

        logger.info("Successfully synced districts")
    else:
        logger.info("No new district data to sync")

    if events:
        events_df = pl.concat(events)

        logger.info(f"Upserting {len(events_df)} events to database")

        db.upsert(
            events_df,
            table_name="events",
            conflict_key="key",
        )

        logger.info("Successfully synced events")
    else:
        logger.info("No new event data to sync")

    if etags:
        TypeAdapter(list[ETag]).validate_python(etags)

        etags_df = pl.DataFrame(etags)

        db.upsert(
            etags_df,
            table_name="etags",
            conflict_key="endpoint",
        )

        logger.debug(f"Updated {len(etags)} ETag(s)")

    logger.info("Event and district sync completed successfully")
