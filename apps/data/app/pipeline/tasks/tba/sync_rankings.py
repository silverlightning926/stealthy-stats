from time import sleep

import polars as pl
from prefect import task
from pydantic import TypeAdapter

from app.models import ETag
from app.services import DBService, TBAService
from app.services.tba import _TBAEndpoint


# TODO: Add Logging To Sync Team Task
@task(
    name="Sync Rankings",
    description="Sync FRC rankings from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_rankings(active_only: bool = False):
    tba = TBAService()
    db = DBService()

    rankings: list[pl.DataFrame] = []
    ranking_infos: list[pl.DataFrame] = []

    etags: list[dict[str, str]] = []

    for event in db.get_event_keys(active_only=active_only):
        etag_key = _TBAEndpoint.RANKINGS.build(event_key=event)

        result = tba.get_rankings(
            event_key=event,
            etag=db.get_etag(endpoint=etag_key),
        )

        if result is None:  # ETag Hit:
            continue  # Skip to next loop iteration

        event_rankings, event_rankings_info, etag = result

        rankings.append(event_rankings)
        ranking_infos.append(event_rankings_info)

        if etag:
            etags.append({"endpoint": etag_key, "etag": etag})

        sleep(3.0)

    if ranking_infos:
        ranking_infos_df = pl.concat(ranking_infos)
        db.upsert(
            ranking_infos_df,
            table_name="event_ranking_info",
            conflict_key="event_key",
        )

    if rankings:
        rankings_df = pl.concat(rankings)
        db.upsert(
            rankings_df,
            table_name="rankings",
            conflict_key=["event_key", "team_key"],
        )

    if etags:
        TypeAdapter(list[ETag]).validate_python(etags)

        etags_df = pl.DataFrame(etags)

        db.upsert(
            etags_df,
            table_name="etags",
            conflict_key="endpoint",
        )
