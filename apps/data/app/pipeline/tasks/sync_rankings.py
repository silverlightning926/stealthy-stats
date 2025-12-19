from time import sleep

import polars as pl
from prefect import task
from prefect.logging import get_run_logger

from app.services import db, tba
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
    logger.info(f"Starting ranking sync with sync_type={sync_type.value}")

    event_keys = db.get_event_keys(sync_type=sync_type)
    etags = db.get_etags(_TBAEndpoint.RANKINGS)
    valid_team_keys = db.get_team_keys()

    logger.info(f"Syncing rankings for {len(event_keys)} events")

    for idx, event_key in enumerate(event_keys, start=1):
        etag_key = _TBAEndpoint.RANKINGS.build(event_key=event_key)
        result = tba.get_rankings(
            event_key=event_key,
            etag=etags.get(etag_key),
        )

        if result is None:
            logger.debug(
                f"[{idx}/{len(event_keys)}] No updates for {event_key} (cached)"
            )
            sleep(0.5)
            continue

        rankings_df, ranking_event_info_df, etag = result
        logger.debug(
            f"[{idx}/{len(event_keys)}] Retrieved {len(rankings_df)} rankings, {len(ranking_event_info_df)} ranking event info for {event_key}"
        )

        rankings_df = rankings_df.filter(pl.col("team_key").is_in(valid_team_keys))

        if not ranking_event_info_df.is_empty():
            db.upsert(
                ranking_event_info_df,
                table_name="ranking_event_infos",
                conflict_key="event_key",
            )

        if not rankings_df.is_empty():
            db.upsert(
                rankings_df,
                table_name="rankings",
                conflict_key=["event_key", "team_key"],
            )

        if etag:
            etag_df = pl.DataFrame([{"endpoint": etag_key, "etag": etag}])
            db.upsert(
                etag_df,
                table_name="etags",
                conflict_key=["endpoint"],
            )

        sleep(0.5)

    logger.info("Ranking sync completed successfully")
