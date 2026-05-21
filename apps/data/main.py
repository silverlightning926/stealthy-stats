from prefect import serve
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import func, select

from app.models.tba import Alliance, Event, Match, Ranking, Team
from app.pipeline.flows import full_sync, live_sync, year_sync
from app.services import DBService


class _ScheduleConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    full_sync_cron: str = Field("0 0 1 * *", validation_alias="FULL_SYNC_CRON")
    year_sync_cron: str = Field("0 0 * * 3", validation_alias="YEAR_SYNC_CRON")
    live_sync_cron: str = Field("*/5 * * * *", validation_alias="LIVE_SYNC_CRON")


def main():
    db = DBService()
    try:
        with db.get_session() as session:
            team_count = session.scalar(select(func.count()).select_from(Team))
            event_count = session.scalar(select(func.count()).select_from(Event))
            match_count = session.scalar(select(func.count()).select_from(Match))
            ranking_count = session.scalar(select(func.count()).select_from(Ranking))
            alliance_count = session.scalar(select(func.count()).select_from(Alliance))

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

    schedule = _ScheduleConfig()

    full_sync_deployment = full_sync.to_deployment(
        name="full-sync-deployment",
        cron=schedule.full_sync_cron,
    )

    year_sync_deployment = year_sync.to_deployment(
        name="year-sync-deployment",
        cron=schedule.year_sync_cron,
    )

    live_sync_deployment = live_sync.to_deployment(
        name="live-sync-deployment",
        cron=schedule.live_sync_cron,
    )

    serve(full_sync_deployment, year_sync_deployment, live_sync_deployment)  # type: ignore


if __name__ == "__main__":
    main()
