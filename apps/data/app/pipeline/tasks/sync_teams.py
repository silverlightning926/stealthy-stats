from time import sleep

import polars as pl
from prefect import task
from prefect.logging import get_run_logger

from app.services import db, tba
from app.services.tba import _TBAEndpoint
from app.utils.batch_accumulator import BatchAccumulator


@task(
    name="Sync Teams",
    description="Sync FRC teams from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_teams(batch_size: int = 5):
    logger = get_run_logger()
    logger.info(f"Starting team sync with batch_size={batch_size}")

    accumulator = BatchAccumulator(batch_size=batch_size)

    page_num = 0
    max_pages = 50

    etags = db.get_etags(_TBAEndpoint.TEAMS)

    logger.info(f"Syncing teams (max {max_pages} pages)")

    while page_num < max_pages:
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

        logger.debug(f"[Page {page_num}/{max_pages}] Retrieved {len(teams_df)} teams")

        accumulator.add_data("teams", teams_df)
        if etag:
            accumulator.add_etag(etag_key, etag)

        page_num += 1

        if accumulator.should_flush(page_num, max_pages):
            logger.info(f"[Page {page_num}/{max_pages}] Flushing batch to database")

            if accumulator.get_data("teams"):
                combined = pl.concat(accumulator.get_data("teams"))
                db.upsert(combined, table_name="teams", conflict_key="key")
                accumulator.clear_data("teams")

            if accumulator.etag_updates:
                combined = pl.DataFrame(accumulator.etag_updates)
                db.upsert(
                    combined,
                    table_name="etags",
                    conflict_key=["endpoint"],
                )

                accumulator.clear_etags()

        sleep(0.5)

    if accumulator.has_data():
        logger.info("Flushing final batch to database")

        if accumulator.get_data("teams"):
            combined = pl.concat(accumulator.get_data("teams"))
            db.upsert(combined, table_name="teams", conflict_key="key")

        if accumulator.etag_updates:
            combined = pl.DataFrame(accumulator.etag_updates)
            db.upsert(
                combined,
                table_name="etags",
                conflict_key=["endpoint"],
            )

    logger.info(f"Team sync completed successfully (processed {page_num} pages)")
