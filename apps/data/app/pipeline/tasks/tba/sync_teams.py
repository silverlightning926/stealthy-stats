from time import sleep

import polars as pl
from prefect import task

from app.services import DBService, TBAService


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

    # TODO: Change TBA Team Sync To Handle Page Count Dynamically
    for page_num in range(0, 30):
        # TODO: Add Etag Fetching & Caching
        page = tba.get_teams(page=page_num)

        if page:
            if not page.data.is_empty():
                teams.append(page.data)

        sleep(1.5)

    if teams:
        db.upsert(pl.concat(teams), table_name="teams", conflict_key="key")
