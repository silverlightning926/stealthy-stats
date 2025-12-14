from time import sleep

import polars as pl
from prefect import get_run_logger, task
from pydantic import TypeAdapter

from app.models import ETag
from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint


@task(
    name="Sync Teams",
    description="Sync FRC teams from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_teams():
    logger = get_run_logger()
    logger.info("Starting team sync from The Blue Alliance")

    tba = TBAService()
    db = DBService()

    teams_list: list[pl.DataFrame] = []
    etags_list: list[dict[str, str]] = []

    # Upper bound for safety - loop breaks when empty page is reached
    for page_num in range(0, 50):
        etag_key = _TBAEndpoint.TEAMS.build(page=str(page_num))

        result = tba.get_teams(
            page=page_num,
            etag=db.get_etag(endpoint=etag_key),
        )

        if result is None:  # ETag cache hit
            logger.debug(f"Cache hit for teams page {page_num}")
            continue

        page_teams_df, etag = result

        if page_teams_df.is_empty():  # Reached end of data
            logger.info(f"Reached end of teams data at page {page_num}")
            break

        logger.debug(f"Retrieved {len(page_teams_df)} teams from page {page_num}")
        teams_list.append(page_teams_df)

        if etag:
            etags_list.append({"endpoint": etag_key, "etag": etag})

        sleep(2.0)

    if teams_list:
        teams_df = pl.concat(teams_list)
        logger.info(f"Upserting {len(teams_df)} teams to database")

        db.upsert(
            teams_df,
            table_name="teams",
            conflict_key="key",
        )
        logger.info("Successfully synced teams")
    else:
        logger.info("No new team data to sync")

    if etags_list:
        TypeAdapter(list[ETag]).validate_python(etags_list)
        etags_df = pl.DataFrame(etags_list)

        db.upsert(
            etags_df,
            table_name="etags",
            conflict_key="endpoint",
        )
        logger.debug(f"Updated {len(etags_list)} ETag(s)")

    logger.info("Team sync completed successfully")
