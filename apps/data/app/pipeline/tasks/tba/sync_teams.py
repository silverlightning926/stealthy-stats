from time import sleep

import polars as pl
from prefect import task
from pydantic import TypeAdapter

from app.models import ETag
from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint


# TODO: Add Logging To Sync Team Task
@task(
    name="Sync Teams",
    description="Syncs FRC teams from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_teams():
    tba = TBAService()
    db = DBService()

    teams: list[pl.DataFrame] = []
    etags: list[dict[str, str]] = []

    # Upper bound for safety - should break loop if it hits an empty page before upper bound
    for page_num in range(0, 50):
        etag_key = _TBAEndpoint.TEAMS.build(page=str(page_num))

        result = tba.get_teams(
            page=page_num,
            etag=db.get_etag(endpoint=etag_key),
        )

        if result is None:  # ETag Hit:
            continue  # Skip to the next loop iteration

        page_teams, etag = result

        if page_teams.is_empty():  # Reached Empty Page:
            break  # Break out of the loop

        teams.append(page_teams)

        if etag:
            etags.append({"endpoint": etag_key, "etag": etag})

        sleep(1.5)

    if teams:
        teams_df = pl.concat(teams)

        db.upsert(
            teams_df,
            table_name="teams",
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
