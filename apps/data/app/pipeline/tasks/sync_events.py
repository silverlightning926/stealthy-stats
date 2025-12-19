from datetime import datetime
from time import sleep

import polars as pl
from prefect import task

from app.services import DBService, TBAService
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
    tba = TBAService()
    db = DBService()
    accumulator = BatchAccumulator(batch_size=batch_size)

    current_year = datetime.now().year
    if sync_type == SyncType.FULL:
        start_year, end_year = 1992, current_year
    else:
        start_year, end_year = current_year, current_year

    year_count = 0
    total_years = end_year - start_year + 1

    etags = db.get_etags(_TBAEndpoint.EVENTS)

    for year in range(start_year, end_year + 1):
        if year == 2021:
            continue

        year_count += 1
        etag_key = _TBAEndpoint.EVENTS.build(year=str(year))
        result = tba.get_events(
            year=year,
            etag=etags.get(etag_key),
        )

        if result is None:
            sleep(0.5)
            continue

        events_df, event_districts_df, etag = result

        accumulator.add_data("events", events_df)
        accumulator.add_data("event_districts", event_districts_df)
        if etag:
            accumulator.add_etag(etag_key, etag)

        if accumulator.should_flush(year_count, total_years):
            if accumulator.get_data("event_districts"):
                combined = pl.concat(accumulator.get_data("event_districts"))
                db.upsert(combined, table_name="event_districts", conflict_key="key")
                accumulator.clear_data("event_districts")

            if accumulator.get_data("events"):
                combined = pl.concat(accumulator.get_data("events"))
                db.upsert(combined, table_name="events", conflict_key="key")
                accumulator.clear_data("events")

            if accumulator.etag_updates:
                combined = pl.DataFrame(accumulator.etag_updates)
                db.upsert(
                    combined,
                    table_name="etags",
                    conflict_key=["endpoint"],
                )

                accumulator.clear_etags()

        sleep(0.5)

    if accumulator.has_data():
        if accumulator.get_data("event_districts"):
            combined = pl.concat(accumulator.get_data("event_districts"))
            db.upsert(combined, table_name="event_districts", conflict_key="key")

        if accumulator.get_data("events"):
            combined = pl.concat(accumulator.get_data("events"))
            db.upsert(combined, table_name="events", conflict_key="key")

        if accumulator.etag_updates:
            combined = pl.DataFrame(accumulator.etag_updates)
            db.upsert(
                combined,
                table_name="etags",
                conflict_key=["endpoint"],
            )
