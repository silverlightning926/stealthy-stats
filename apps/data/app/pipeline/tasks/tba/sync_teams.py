from time import sleep

import polars as pl
from prefect import task
from pydantic import TypeAdapter

from app.models.tba import Team
from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint


# TODO: Add Logging To Sync Team Task
@task(
    name="Sync Teams",
    description="Sync FRC Teams From The Blue ALliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_teams():
    tba = TBAService()
    db = DBService()

    teams: list[pl.DataFrame] = []

    # Upper bound for safety - should break loop if it hits an empty page before upper bound
    for page_num in range(0, 50):
        etag_key = _TBAEndpoint.TEAMS.add_dynamic(str(page_num))

        page = tba.get_teams(
            page=page_num,
            etag=db.get_etag(endpoint=etag_key),
        )

        if page is None:
            continue  # ETag Hit - Skip to the next loop iteration

        if page.data.is_empty():
            break  # Reached Empty Page - Break out of the loop

        teams.append(page.data)

        if page.etag:
            db.upsert_etag(
                endpoint=etag_key,
                etag=page.etag,
            )

        sleep(1.5)

    if teams:
        teams_df = pl.concat(teams)

        TypeAdapter(list[Team]).validate_python(teams_df.to_dicts())

        db.upsert(
            teams_df,
            table_name="teams",
            conflict_key="key",
        )
