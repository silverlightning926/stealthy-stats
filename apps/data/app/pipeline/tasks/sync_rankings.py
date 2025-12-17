from time import sleep

import polars as pl
from prefect import get_run_logger, task

from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint
from app.types import SyncType


@task(
    name="Sync Rankings",
    description="Sync FRC rankings and ranking event info from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_rankings(sync_type: SyncType = SyncType.FULL):
    logger = get_run_logger()

    logger.info(
        f"Starting rankings sync from The Blue Alliance (sync_type={sync_type.value})"
    )

    tba = TBAService()
    db = DBService()

    event_keys = db.get_event_keys(sync_type=sync_type)
    logger.info(f"Found {len(event_keys)} events to process")

    total_rankings = 0
    total_ranking_event_infos = 0

    for event_key in event_keys:
        etag_key = _TBAEndpoint.RANKINGS.build(event_key=event_key)

        result = tba.get_rankings(
            event_key=event_key,
            etag=db.get_etag(endpoint=etag_key),
        )

        if result is None:  # ETag cache hit
            logger.debug(f"Cache hit for event {event_key}")
            continue

        event_rankings_df, event_ranking_event_info_df, etag = result

        logger.debug(
            f"Retrieved {len(event_rankings_df)} rankings and {len(event_ranking_event_info_df)} ranking event info record for event {event_key}"
        )

        if not event_ranking_event_info_df.is_empty():
            db.upsert(
                event_ranking_event_info_df,
                table_name="ranking_event_infos",
                conflict_key="event_key",
            )
            total_ranking_event_infos += len(event_ranking_event_info_df)
            logger.info(
                f"Upserted {len(event_ranking_event_info_df)} ranking event info record for event {event_key}"
            )

        if not event_rankings_df.is_empty():
            original_length = len(event_rankings_df)
            event_rankings_df = event_rankings_df.filter(
                pl.col("team_key").is_in(db.get_team_keys())
            )

            removed_count = original_length - len(event_rankings_df)
            if removed_count > 0:
                logger.debug(
                    f"Removed {removed_count} ghost teams for event {event_key}"
                )

            if not event_rankings_df.is_empty():
                db.upsert(
                    event_rankings_df,
                    table_name="rankings",
                    conflict_key=["event_key", "team_key"],
                )
                total_rankings += len(event_rankings_df)
                logger.info(
                    f"Upserted {len(event_rankings_df)} rankings for event {event_key}"
                )

        if etag:
            db.upsert_etag(endpoint=etag_key, etag=etag)

        sleep(3.0)

    logger.info(
        f"Successfully synced {total_ranking_event_infos} ranking event info records"
    )
    logger.info(f"Successfully synced {total_rankings} rankings")

    logger.info(f"Rankings sync completed successfully (sync_type={sync_type.value})")
