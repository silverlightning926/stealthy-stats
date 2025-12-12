from time import sleep

import polars as pl
from prefect import task
from pydantic import TypeAdapter

from app.models import ETag
from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint


# TODO: Add Logging To Sync Team Task
@task(
    name="Sync Alliances",
    description="Sync FRC alliances from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_alliances(active_only: bool = False):
    tba = TBAService()
    db = DBService()

    alliances: list[pl.DataFrame] = []

    etags: list[dict[str, str]] = []

    for event in db.get_event_keys(active_only=active_only):
        etag_key = _TBAEndpoint.ALLIANCES.build(event_key=event)

        result = tba.get_alliances(
            event_key=event,
            etag=db.get_etag(endpoint=etag_key),
        )

        if result is None:  # ETag Hit:
            continue  # Skip to next loop iteration

        event_alliances, etag = result

        alliances.append(event_alliances)

        if etag:
            etags.append({"endpoint": etag_key, "etag": etag})

        sleep(3.0)

    if alliances:
        alliances_df = pl.concat(alliances)
        db.upsert(
            alliances_df,
            table_name="alliances",
            conflict_key=["event_key", "name"],
        )

    if etags:
        TypeAdapter(list[ETag]).validate_python(etags)

        etags_df = pl.DataFrame(etags)

        db.upsert(
            etags_df,
            table_name="etags",
            conflict_key="endpoint",
        )
