from datetime import datetime
from time import sleep

import polars as pl
from prefect import task
from pydantic import TypeAdapter

from app.models import ETag
from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint


# TODO: Add Logging To Sync Team Task
@task(
    name="Sync Events",
    description="Sync FRC events from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_events():
    tba = TBAService()
    db = DBService()

    events: list[pl.DataFrame] = []
    etags: list[dict[str, str]] = []

    for year in range(1992, datetime.now().year + 1):
        if year == 2021:
            continue

        etag_key = _TBAEndpoint.EVENTS.build(year=str(year))

        year = tba.get_events(
            year=year,
            etag=db.get_etag(endpoint=etag_key),
        )

        if year is None:  # ETag Hit:
            continue  # Skip to next loop iteration

        events.append(year.data)

        if year.etag:
            etags.append({"endpoint": etag_key, "etag": year.etag})

        sleep(1.5)

    if events:
        events_df = pl.concat(events)

        db.upsert(
            events_df,
            table_name="events",
            conflict_key="key",
        )

        if etags:
            TypeAdapter(list[ETag]).validate_python(etags)

            etags_df = pl.DataFrame(etags)

            db.upsert(
                etags_df,
                table_name="etags",
                conflict_key="endpoint",
            )
