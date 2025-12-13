from datetime import timedelta

from prefect import serve

from app.pipeline.flows import full_sync, live_sync
from app.services import DBService


def main():
    db = DBService()
    try:
        with db.get_session() as session:
            from sqlmodel import func, select

            from app.models.tba import Alliance, Event, Match, Ranking, Team

            team_count = session.exec(select(func.count(Team.key))).one()  # pyright: ignore[reportArgumentType]
            event_count = session.exec(select(func.count(Event.key))).one()  # pyright: ignore[reportArgumentType]
            match_count = session.exec(select(func.count(Match.key))).one()  # pyright: ignore[reportArgumentType]
            ranking_count = session.exec(select(func.count(Ranking.event_key))).one()  # pyright: ignore[reportArgumentType]
            alliance_count = session.exec(select(func.count(Alliance.event_key))).one()  # pyright: ignore[reportArgumentType]

            if any(
                [
                    team_count == 0,
                    event_count == 0,
                    match_count == 0,
                    ranking_count == 0,
                    alliance_count == 0,
                ]
            ):
                full_sync()

    except Exception:
        full_sync()

    full_sync_deployment = full_sync.to_deployment(
        name="full-sync-deployment", cron="0 0 * * 2,5"
    )

    live_sync_deployment = live_sync.to_deployment(
        name="live-sync-deployment", interval=timedelta(minutes=10)
    )

    serve(full_sync_deployment, live_sync_deployment)  # type: ignore


if __name__ == "__main__":
    main()
