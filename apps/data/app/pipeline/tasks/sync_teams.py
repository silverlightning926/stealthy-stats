from time import sleep

from prefect import get_run_logger, task

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

    total_teams = 0

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

        db.upsert(
            page_teams_df,
            table_name="teams",
            conflict_key="key",
        )
        total_teams += len(page_teams_df)
        logger.info(f"Upserted {len(page_teams_df)} teams from page {page_num}")

        if etag:
            db.upsert_etag(endpoint=etag_key, etag=etag)

        sleep(2.0)

    logger.info(f"Successfully synced {total_teams} teams")

    logger.info("Team sync completed successfully")
