from datetime import timedelta

from prefect import serve
from sqlalchemy import func, select

from app.models.tba import Alliance, Event, EventTeam, Match, Ranking, Team
from app.pipeline.flows import full_sync, live_sync, year_sync
from app.services import DBService


def main():
    db = DBService()
    try:
        with db.get_session() as session:
            team_count = session.scalar(select(func.count()).select_from(Team))
            event_count = session.scalar(select(func.count()).select_from(Event))
            event_team_count = session.scalar(
                select(func.count()).select_from(EventTeam)
            )
            match_count = session.scalar(select(func.count()).select_from(Match))
            ranking_count = session.scalar(select(func.count()).select_from(Ranking))
            alliance_count = session.scalar(select(func.count()).select_from(Alliance))

            if any(
                [
                    team_count == 0,
                    event_count == 0,
                    event_team_count == 0,
                    match_count == 0,
                    ranking_count == 0,
                    alliance_count == 0,
                ]
            ):
                full_sync()

    except Exception:
        full_sync()

    full_sync_deployment = full_sync.to_deployment(
        name="full-sync-deployment",
        cron="0 0 1,15 * *",  # Midnight on the 1st and 15th of the month
    )

    year_sync_deployment = year_sync.to_deployment(
        name="year-sync-deployment",
        cron="0 0 * * 1,4",  # Midnight on Mondays and Thursdays
    )

    live_sync_deployment = live_sync.to_deployment(
        name="live-sync-deployment",
        interval=timedelta(minutes=10),
    )

    serve(full_sync_deployment, year_sync_deployment, live_sync_deployment)  # type: ignore


if __name__ == "__main__":
    main()
