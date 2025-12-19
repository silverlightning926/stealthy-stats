from datetime import datetime
from time import sleep

import polars as pl
from prefect import task
from prefect.logging import get_run_logger

from app.services import db, tba
from app.services.tba import _TBAEndpoint
from app.types import SyncType


@task(
    name="Sync Events",
    description="Sync FRC events and districts from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_events(sync_type: SyncType = SyncType.FULL):
    logger = get_run_logger()
    logger.info(f"Starting event sync with sync_type={sync_type.value}")

    current_year = datetime.now().year
    if sync_type == SyncType.FULL:
        start_year, end_year = 1992, current_year
    else:
        start_year, end_year = current_year, current_year

    year_count = 0
    total_years = end_year - start_year + 1

    logger.info(f"Syncing events from {start_year} to {end_year} ({total_years} years)")

    etags = db.get_etags(_TBAEndpoint.EVENTS)

    for year in range(start_year, end_year + 1):
        if year == 2021:
            logger.debug("Skipping year 2021 (no events)")
            continue

        year_count += 1
        logger.debug(f"[{year_count}/{total_years}] Processing year {year}")

        etag_key = _TBAEndpoint.EVENTS.build(year=str(year))
        result = tba.get_events(
            year=year,
            etag=etags.get(etag_key),
        )

        if result is None:
            logger.debug(
                f"[{year_count}/{total_years}] No updates for year {year} (cached)"
            )
            sleep(0.5)
            continue

        events_df, event_districts_df, etag = result

        upserts = []

        if not event_districts_df.is_empty():
            upserts.append((event_districts_df, "event_districts", "key"))

        if not events_df.is_empty():
            upserts.append((events_df, "events", "key"))

        if etag:
            etag_df = pl.DataFrame([{"endpoint": etag_key, "etag": etag}])
            upserts.append((etag_df, "etags", ["endpoint"]))

        if upserts:
            logger.info(
                f"[{year_count}/{total_years}] Year {year}: "
                f"{len(events_df)} events, {len(event_districts_df)} districts"
            )
            db.upsert_many(upserts)

        sleep(0.5)

    logger.info("Event sync completed successfully")
