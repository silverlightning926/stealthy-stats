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
    name="Sync Districts",
    description="Sync FRC districts from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_districts():
    tba = TBAService()
    db = DBService()

    districts: list[pl.DataFrame] = []
    etags: list[dict[str, str]] = []

    for year in range(1992, datetime.now().year + 1):
        if year == 2021:
            continue

        etag_key = _TBAEndpoint.DISTRICTS.build(year=str(year))

        year = tba.get_districts(
            year=year,
            etag=db.get_etag(endpoint=etag_key),
        )

        if year is None:  # ETag Hit:
            continue  # Skip to next loop iteration

        districts.append(year.data)

        if year.etag:
            etags.append({"endpoint": etag_key, "etag": year.etag})

        sleep(1.5)

    if districts:
        districts_df = pl.concat(districts)

        db.upsert(
            districts_df,
            table_name="districts",
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
