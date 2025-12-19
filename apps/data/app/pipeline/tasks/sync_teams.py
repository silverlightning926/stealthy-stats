from time import sleep

import polars as pl
from prefect import task
from prefect.logging import get_run_logger

from app.services import db, tba
from app.services.tba import _TBAEndpoint


@task(
    name="Sync Teams",
    description="Sync FRC teams from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_teams():
    logger = get_run_logger()
    logger.info("Starting team sync")

    page_num = 0
    max_pages = 50

    etags = db.get_etags(_TBAEndpoint.TEAMS)

    logger.info(f"Syncing teams (max {max_pages} pages)")

    while page_num < max_pages:
        logger.debug(f"[Page {page_num}] Processing teams")

        etag_key = _TBAEndpoint.TEAMS.build(page=str(page_num))
        result = tba.get_teams(
            page=page_num,
            etag=etags.get(etag_key),
        )

        if result is None:
            logger.debug(f"[Page {page_num}/{max_pages}] No updates (cached)")
            sleep(0.5)
            page_num += 1
            continue

        teams_df, etag = result

        if teams_df.is_empty():
            logger.info(f"Reached end of teams at page {page_num}")
            break

        upserts = []

        upserts.append((teams_df, "teams", "key"))

        if etag:
            etag_df = pl.DataFrame([{"endpoint": etag_key, "etag": etag}])
            upserts.append((etag_df, "etags", ["endpoint"]))

        logger.info(f"[Page {page_num}] {len(teams_df)} teams")
        db.upsert_many(upserts)

        page_num += 1
        sleep(0.5)

    logger.info(f"Team sync completed successfully (processed {page_num} pages)")
