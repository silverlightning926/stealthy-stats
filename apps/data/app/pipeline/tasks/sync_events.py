from datetime import datetime
from time import sleep

import polars as pl
from prefect import task
from prefect.logging import get_run_logger

from app.services import db, tba
from app.services.tba import _TBAEndpoint
from app.types import SyncType
from app.utils.batch_accumulator import BatchAccumulator


@task(
    name="Sync Events",
    description="Sync FRC events and districts from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_events(sync_type: SyncType = SyncType.FULL, batch_size: int = 5):
    logger = get_run_logger()
    logger.info(
        f"Starting event sync with sync_type={sync_type.value}, batch_size={batch_size}"
    )

    accumulator = BatchAccumulator(batch_size=batch_size)

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
        logger.debug(
            f"[{year_count}/{total_years}] Retrieved {len(events_df)} events, {len(event_districts_df)} event districts for year {year}"
        )

        accumulator.add_data("events", events_df)
        accumulator.add_data("event_districts", event_districts_df)
        if etag:
            accumulator.add_etag(etag_key, etag)

        if accumulator.should_flush(year_count, total_years):
            logger.info(f"[{year_count}/{total_years}] Flushing batch to database")

            if accumulator.get_data("event_districts"):
                combined = pl.concat(accumulator.get_data("event_districts"))
                db.upsert(combined, table_name="event_districts", conflict_key="key")
                accumulator.clear_data("event_districts")

            if accumulator.get_data("events"):
                combined = pl.concat(accumulator.get_data("events"))
                db.upsert(combined, table_name="events", conflict_key="key")
                accumulator.clear_data("events")

            if accumulator.has_etags():
                combined = pl.DataFrame(accumulator.get_etags())
                db.upsert(
                    combined,
                    table_name="etags",
                    conflict_key=["endpoint"],
                )

                accumulator.clear_etags()

        sleep(0.5)

    if accumulator.has_data():
        logger.info("Flushing final batch to database")

        if accumulator.get_data("event_districts"):
            combined = pl.concat(accumulator.get_data("event_districts"))
            db.upsert(combined, table_name="event_districts", conflict_key="key")

        if accumulator.get_data("events"):
            combined = pl.concat(accumulator.get_data("events"))
            db.upsert(combined, table_name="events", conflict_key="key")

        if accumulator.has_etags():
            combined = pl.DataFrame(accumulator.get_etags())
            db.upsert(
                combined,
                table_name="etags",
                conflict_key=["endpoint"],
            )

    logger.info("Event sync completed successfully")
