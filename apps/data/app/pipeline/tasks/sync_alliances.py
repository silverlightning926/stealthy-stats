from time import sleep

import polars as pl
from prefect import task
from prefect.logging import get_run_logger

from app.services import db, tba
from app.services.tba import _TBAEndpoint
from app.types import SyncType


@task(
    name="Sync Alliances",
    description="Sync FRC alliances and alliance teams from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_alliances(sync_type: SyncType = SyncType.FULL):
    logger = get_run_logger()
    logger.info(f"Starting alliance sync with sync_type={sync_type.value}")

    event_keys = db.get_event_keys(sync_type=sync_type)
    etags = db.get_etags(_TBAEndpoint.ALLIANCES)
    valid_team_keys = db.get_team_keys()

    logger.info(f"Syncing alliances for {len(event_keys)} events")

    for idx, event_key in enumerate(event_keys, start=1):
        etag_key = _TBAEndpoint.ALLIANCES.build(event_key=event_key)
        result = tba.get_alliances(
            event_key=event_key,
            etag=etags.get(etag_key),
        )

        if result is None:
            logger.debug(
                f"[{idx}/{len(event_keys)}] No updates for {event_key} (cached)"
            )
            sleep(0.5)
            continue

        alliances_df, alliance_teams_df, etag = result
        logger.debug(
            f"[{idx}/{len(event_keys)}] Retrieved {len(alliances_df)} alliances, {len(alliance_teams_df)} alliance teams for {event_key}"
        )

        alliance_teams_df = alliance_teams_df.filter(
            pl.col("team_key").is_in(valid_team_keys)
        )

        if not alliances_df.is_empty():
            db.upsert(
                alliances_df,
                table_name="alliances",
                conflict_key=["event_key", "name"],
            )

        if not alliance_teams_df.is_empty():
            db.upsert(
                alliance_teams_df,
                table_name="alliance_teams",
                conflict_key=["event_key", "alliance_name", "team_key"],
            )

        if etag:
            etag_df = pl.DataFrame([{"endpoint": etag_key, "etag": etag}])
            db.upsert(
                etag_df,
                table_name="etags",
                conflict_key=["endpoint"],
            )

        sleep(0.5)

    logger.info("Alliance sync completed successfully")
