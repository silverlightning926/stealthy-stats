from time import sleep

import polars as pl
from prefect import task
from prefect.logging import get_run_logger

from app.services import db, tba
from app.services.tba import _TBAEndpoint
from app.types import SyncType


@task(
    name="Sync Event Teams",
    description="Sync FRC event team participation from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_event_teams(sync_type: SyncType = SyncType.FULL):
    logger = get_run_logger()
    logger.info(f"Starting event teams sync with sync_type={sync_type.value}")

    event_keys = db.get_event_keys(sync_type=sync_type)
    etags = db.get_etags(_TBAEndpoint.EVENT_TEAMS)
    valid_team_keys = db.get_team_keys()

    logger.info(f"Syncing event teams for {len(event_keys)} events")

    for idx, event_key in enumerate(event_keys, start=1):
        logger.debug(f"[{idx}/{len(event_keys)}] Processing {event_key}")

        etag_key = _TBAEndpoint.EVENT_TEAMS.build(event_key=event_key)
        result = tba.get_event_teams(
            event_key=event_key,
            etag=etags.get(etag_key),
        )

        if result is None:
            logger.debug(
                f"[{idx}/{len(event_keys)}] No updates for {event_key} (cached)"
            )
            sleep(0.5)
            continue

        event_teams_df, etag = result

        event_teams_df = event_teams_df.filter(
            pl.col("team_key").is_in(valid_team_keys)
        )

        upserts = []

        if not event_teams_df.is_empty():
            upserts.append(
                (
                    event_teams_df,
                    "event_teams",
                    ["event_key", "team_key"],
                )
            )

        if etag:
            etag_df = pl.DataFrame([{"endpoint": etag_key, "etag": etag}])
            upserts.append((etag_df, "etags", ["endpoint"]))

        if upserts:
            logger.info(
                f"[{idx}/{len(event_keys)}] {event_key}: {len(event_teams_df)} teams"
            )
            db.upsert_many(upserts)

        sleep(0.5)

    logger.info("Event teams sync completed successfully")
