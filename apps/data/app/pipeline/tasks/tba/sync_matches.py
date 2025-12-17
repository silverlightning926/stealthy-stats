from time import sleep

import polars as pl
from prefect import get_run_logger, task
from pydantic import TypeAdapter

from app.models import ETag
from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint
from app.types import SyncType


@task(
    name="Sync Matches",
    description="Sync FRC matches, match alliances, and match alliance teams from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_matches(sync_type: SyncType = SyncType.FULL):
    logger = get_run_logger()

    logger.info(
        f"Starting match sync from The Blue Alliance (sync_type={sync_type.value})"
    )

    tba = TBAService()
    db = DBService()

    matches_list: list[pl.DataFrame] = []
    match_alliances_list: list[pl.DataFrame] = []
    match_alliance_teams_list: list[pl.DataFrame] = []
    etags_list: list[dict[str, str]] = []

    event_keys = db.get_event_keys(sync_type=sync_type)
    logger.info(f"Found {len(event_keys)} events to process")

    for event_key in event_keys:
        etag_key = _TBAEndpoint.MATCHES.build(event_key=event_key)

        result = tba.get_matches(
            event_key=event_key,
            etag=db.get_etag(endpoint=etag_key),
        )

        if result is None:  # ETag cache hit
            logger.debug(f"Cache hit for event {event_key}")
            continue

        (
            event_matches_df,
            event_match_alliances_df,
            event_match_alliance_teams_df,
            etag,
        ) = result

        logger.debug(
            f"Retrieved {len(event_matches_df)} matches, {len(event_match_alliances_df)} match alliances, "
            f"and {len(event_match_alliance_teams_df)} match alliance teams for event {event_key}"
        )
        matches_list.append(event_matches_df)
        match_alliances_list.append(event_match_alliances_df)
        match_alliance_teams_list.append(event_match_alliance_teams_df)

        if etag:
            etags_list.append({"endpoint": etag_key, "etag": etag})

        sleep(3.0)

    if matches_list:
        matches_df = pl.concat(matches_list)
        logger.info(f"Upserting {len(matches_df)} matches to database")

        db.upsert(
            matches_df,
            table_name="matches",
            conflict_key="key",
        )
        logger.info("Successfully synced matches")
    else:
        logger.info("No new match data to sync")

    if match_alliances_list:
        match_alliances_df = pl.concat(match_alliances_list)
        logger.info(f"Upserting {len(match_alliances_df)} match alliances to database")

        db.upsert(
            match_alliances_df,
            table_name="match_alliances",
            conflict_key=["match_key", "alliance_color"],
        )
        logger.info("Successfully synced match alliances")
    else:
        logger.info("No new match alliance data to sync")

    if match_alliance_teams_list:
        match_alliance_teams_df = pl.concat(match_alliance_teams_list)
        original_match_alliance_teams_df_length = len(match_alliance_teams_df)

        match_alliance_teams_df = match_alliance_teams_df.filter(
            pl.col("team_key").is_in(db.get_team_keys())
        )
        logger.info(
            f"Removed {len(match_alliance_teams_df) - original_match_alliance_teams_df_length} ghost teams"
        )

        logger.info(
            f"Upserting {len(match_alliance_teams_df)} match alliance teams to database"
        )

        db.upsert(
            match_alliance_teams_df,
            table_name="match_alliance_teams",
            conflict_key=["match_key", "alliance_color", "team_key"],
        )
        logger.info("Successfully synced match alliance teams")
    else:
        logger.info("No new match alliance team data to sync")

    if etags_list:
        TypeAdapter(list[ETag]).validate_python(etags_list)
        etags_df = pl.DataFrame(etags_list)

        db.upsert(
            etags_df,
            table_name="etags",
            conflict_key="endpoint",
        )
        logger.debug(f"Updated {len(etags_list)} ETag(s)")

    logger.info(f"Match sync completed successfully (sync_type={sync_type.value})")
