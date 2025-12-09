from time import sleep

import polars as pl
from prefect import task
from pydantic import TypeAdapter

from app.models import ETag
from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint


# TODO: Add Logging To Sync Team Task
@task(
    name="Sync Matches",
    description="Sync FRC matches from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_matches():
    tba = TBAService()
    db = DBService()

    matches: list[pl.DataFrame] = []
    match_alliances: list[pl.DataFrame] = []

    etags: list[dict[str, str]] = []

    for event in db.get_event_keys():
        etag_key = _TBAEndpoint.MATCHES.build(event_key=event)

        result = tba.get_matches(
            event_key=event,
            etag=db.get_etag(endpoint=etag_key),
        )

        if result is None:  # ETag Hit:
            continue  # Skip to next loop iteration

        event_matches, event_match_alliances, event_etag = result

        matches.append(event_matches)
        match_alliances.append(event_match_alliances)

        if event_etag:
            etags.append({"endpoint": etag_key, "etag": event_etag})

        sleep(1.5)

    if matches:
        match_alliances_df = pl.concat(match_alliances)
        db.upsert(
            match_alliances_df,
            table_name="match_alliances",
            conflict_key="key",
        )

        matches_df = pl.concat(matches)
        db.upsert(
            matches_df,
            table_name="matches",
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
