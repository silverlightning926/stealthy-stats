from time import sleep

from prefect import get_run_logger, task

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

    event_keys = db.get_event_keys(sync_type=sync_type)
    logger.info(f"Found {len(event_keys)} events to process")

    total_matches = 0
    total_match_alliances = 0
    total_match_alliance_teams = 0

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

        if not event_matches_df.is_empty():
            db.upsert(
                event_matches_df,
                table_name="matches",
                conflict_key="key",
            )
            total_matches += len(event_matches_df)
            logger.info(
                f"Upserted {len(event_matches_df)} matches for event {event_key}"
            )

        if not event_match_alliances_df.is_empty():
            db.upsert(
                event_match_alliances_df,
                table_name="match_alliances",
                conflict_key=["match_key", "alliance_color"],
            )
            total_match_alliances += len(event_match_alliances_df)
            logger.info(
                f"Upserted {len(event_match_alliances_df)} match alliances for event {event_key}"
            )

        if not event_match_alliance_teams_df.is_empty():
            db.upsert(
                event_match_alliance_teams_df,
                table_name="match_alliance_teams",
                conflict_key=["match_key", "alliance_color", "team_key"],
            )
            total_match_alliance_teams += len(event_match_alliance_teams_df)
            logger.info(
                f"Upserted {len(event_match_alliance_teams_df)} match alliance teams for event {event_key}"
            )

        if etag:
            db.upsert_etag(endpoint=etag_key, etag=etag)

        sleep(3.0)

    logger.info(f"Successfully synced {total_matches} matches")
    logger.info(f"Successfully synced {total_match_alliances} match alliances")
    logger.info(
        f"Successfully synced {total_match_alliance_teams} match alliance teams"
    )

    logger.info(f"Match sync completed successfully (sync_type={sync_type.value})")
