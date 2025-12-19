import re
from contextlib import contextmanager
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import polars as pl
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import MetaData, NullPool, Table
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlmodel import Session, SQLModel, create_engine, select
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.models import ETag  # noqa: F401
from app.models.tba import (  # noqa: F401
    Alliance,
    AllianceTeam,
    Event,
    EventDistrict,
    Match,
    MatchAlliance,
    MatchAllianceTeam,
    Ranking,
    RankingEventInfo,
    RankingSortOrderInfo,
    Team,
)
from app.types import SyncType

from .tba import _TBAEndpoint


class _DBConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_url: SecretStr = Field(..., min_length=1, validation_alias="DATABASE_URL")


class DBService:
    def __init__(self):
        self.config = _DBConfig()  # pyright: ignore[reportCallIssue]

        self.engine = create_engine(
            self.config.db_url.get_secret_value(),
            echo=False,
            poolclass=NullPool,
            pool_pre_ping=True,
            connect_args={
                "connect_timeout": 10,
            },
        )

        SQLModel.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self):
        session = Session(self.engine)
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((OperationalError, InterfaceError)),
        reraise=True,
    )
    def upsert(
        self,
        df: pl.DataFrame,
        table_name: str,
        conflict_key: str | list[str] | None = None,
    ):
        with self.get_session() as session:
            records = df.to_dicts()

            if not records:
                return

            metadata = MetaData()
            table = Table(table_name, metadata, autoload_with=self.engine)

            stmt = insert(table).values(records)

            if conflict_key is None:
                conflict_keys = [col.name for col in table.primary_key.columns]
            else:
                conflict_keys = (
                    [conflict_key] if isinstance(conflict_key, str) else conflict_key
                )

            update_cols = {
                c: stmt.excluded[c] for c in df.columns if c not in conflict_keys
            }

            if not update_cols:
                upsert_stmt = stmt.on_conflict_do_nothing(index_elements=conflict_keys)
            else:
                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=conflict_keys,
                    set_=update_cols,
                )

            session.exec(upsert_stmt)

    def get_etags(self, endpoint: _TBAEndpoint) -> dict[str, str]:
        pattern = re.sub(r"\{[^}]+\}", "%", endpoint.value)

        with self.get_session() as session:
            results = session.exec(
                select(ETag.endpoint, ETag.etag).where(
                    ETag.endpoint.like(pattern)  # pyright: ignore[reportAttributeAccessIssue]
                )
            ).all()

            etags = {endpoint: etag for endpoint, etag in results}

            return etags

    def get_team_keys(self) -> set[str]:
        with self.get_session() as session:
            teams = session.exec(select(Team.key)).all()
            team_keys = set(teams)
            return team_keys

    def _is_event_active(self, event: Event) -> bool:
        buffer = timedelta(days=1, hours=2)

        event_tz = ZoneInfo(event.timezone) if event.timezone else ZoneInfo("UTC")
        now_in_event_tz = datetime.now(event_tz).date()

        event_start_with_buffer = event.start_date - buffer
        event_end_with_buffer = event.end_date + buffer

        return event_start_with_buffer <= now_in_event_tz <= event_end_with_buffer

    def get_event_keys(self, sync_type: SyncType = SyncType.FULL) -> list[str]:
        with self.get_session() as session:
            if sync_type == SyncType.FULL:
                # All inactive events, all years
                events = list(
                    session.exec(select(Event).order_by(Event.start_date)).all()  # pyright: ignore[reportArgumentType]
                )
                keys = [
                    event.key for event in events if not self._is_event_active(event)
                ]

            elif sync_type == SyncType.LIVE:
                # Active events, current year only
                events = list(
                    session.exec(
                        select(Event)
                        .where(Event.year == datetime.now().year)
                        .order_by(Event.start_date)  # pyright: ignore[reportArgumentType]
                    ).all()
                )
                keys = [event.key for event in events if self._is_event_active(event)]

            elif sync_type == SyncType.YEAR:
                # Inactive events, current year only
                events = list(
                    session.exec(
                        select(Event)
                        .where(Event.year == datetime.now().year)
                        .order_by(Event.start_date)  # pyright: ignore[reportArgumentType]
                    ).all()
                )
                keys = [
                    event.key for event in events if not self._is_event_active(event)
                ]

            return keys
