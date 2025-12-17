from datetime import datetime
from time import sleep

from prefect import get_run_logger, task

from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint
from app.types import SyncType


@task(
    name="Sync Events",
    description="Sync FRC events and districts from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_events(sync_type: SyncType = SyncType.FULL):
    logger = get_run_logger()

    logger.info(
        f"Starting event sync from The Blue Alliance (sync_type={sync_type.value})"
    )

    tba = TBAService()
    db = DBService()

    if sync_type == SyncType.FULL:
        start_year = 1992
        end_year = datetime.now().year
    elif sync_type == SyncType.LIVE:
        start_year = datetime.now().year
        end_year = datetime.now().year
    elif sync_type == SyncType.YEAR:
        start_year = datetime.now().year
        end_year = datetime.now().year

    logger.info(f"Syncing events from {start_year} to {end_year}")

    total_events = 0
    total_event_districts = 0

    for year in range(start_year, end_year + 1):
        if year == 2021:
            logger.debug("Skipping year 2021 (no competition season)")
            continue

        etag_key = _TBAEndpoint.EVENTS.build(year=str(year))

        result = tba.get_events(
            year=year,
            etag=db.get_etag(endpoint=etag_key),
        )

        if result is None:  # ETag cache hit
            logger.debug(f"Cache hit for year {year}")
            continue

        year_events_df, year_event_districts_df, etag = result

        logger.debug(
            f"Retrieved {len(year_events_df)} events and {len(year_event_districts_df)} districts for year {year}"
        )

        if not year_event_districts_df.is_empty():
            db.upsert(
                year_event_districts_df,
                table_name="event_districts",
                conflict_key="key",
            )
            total_event_districts += len(year_event_districts_df)
            logger.info(
                f"Upserted {len(year_event_districts_df)} event districts for year {year}"
            )

        if not year_events_df.is_empty():
            db.upsert(
                year_events_df,
                table_name="events",
                conflict_key="key",
            )
            total_events += len(year_events_df)
            logger.info(f"Upserted {len(year_events_df)} events for year {year}")

        if etag:
            db.upsert_etag(endpoint=etag_key, etag=etag)

        sleep(2.0)

    logger.info(f"Successfully synced {total_event_districts} event districts")
    logger.info(f"Successfully synced {total_events} events")

    logger.info(f"Event sync completed successfully (sync_type={sync_type.value})")
