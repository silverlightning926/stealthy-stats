from time import sleep

import polars as pl
from prefect import get_run_logger, task
from pydantic import TypeAdapter

from app.models import ETag
from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint


@task(
    name="Sync Teams",
    description="Syncs FRC teams from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_teams():
    logger = get_run_logger()

    logger.info("Starting team sync from The Blue Alliance")

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
            logger.debug(f"Cache hit for teams page {page_num}")
            continue  # Skip to the next loop iteration

        page_teams, etag = result

        if page_teams.is_empty():  # Reached Empty Page:
            logger.info(f"Reached end of teams data at page {page_num}")
            break  # Break out of the loop

        logger.debug(f"Retrieved {len(page_teams)} teams from page {page_num}")
        teams.append(page_teams)

        if etag:
            etags.append({"endpoint": etag_key, "etag": etag})

        sleep(1.5)

    if teams:
        teams_df = pl.concat(teams)

        logger.info(f"Upserting {len(teams_df)} teams to database")

        db.upsert(
            teams_df,
            table_name="teams",
            conflict_key="key",
        )

        logger.info("Successfully synced teams")
    else:
        logger.info("No new team data to sync")

    if etags:
        TypeAdapter(list[ETag]).validate_python(etags)

        etags_df = pl.DataFrame(etags)

        db.upsert(
            etags_df,
            table_name="etags",
            conflict_key="endpoint",
        )

        logger.debug(f"Updated {len(etags)} ETag(s)")

    logger.info("Team sync completed successfully")
