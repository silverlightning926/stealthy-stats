import logging
from contextlib import contextmanager
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import polars as pl
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import MetaData, NullPool, Table
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import ETag  # noqa: F401
from app.models.tba import (  # noqa: F401
    Alliance,
    District,
    Event,
    EventRankingInfo,
    Match,
    MatchAlliance,
    MatchAllianceTeam,
    Ranking,
    RankingInfo,
    Team,
)


class _DBConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_url: SecretStr = Field(..., min_length=1, validation_alias="DATABASE_URL")


class DBService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        self.config = _DBConfig()  # pyright: ignore[reportCallIssue]

        self.logger.info("Initializing database connection")
        self.engine = create_engine(
            self.config.db_url.get_secret_value(),
            echo=False,
            poolclass=NullPool,
            pool_pre_ping=True,
            connect_args={
                "connect_timeout": 10,
            },
        )

        try:
            SQLModel.metadata.create_all(self.engine)
            self.logger.info("Database tables created/verified successfully")
        except Exception as e:
            self.logger.error(f"Failed to create database tables: {e}")
            raise

    @contextmanager
    def get_session(self):
        session = Session(self.engine)
        try:
            yield session
            session.commit()
            self.logger.debug("Database session committed successfully")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Database session error, rolling back: {e}")
            raise
        finally:
            session.close()
            self.logger.debug("Database session closed")

    def upsert(
        self,
        df: pl.DataFrame,
        table_name: str,
        conflict_key: str | list[str] | None = None,
    ):
        record_count = len(df)
        self.logger.info(f"Upserting {record_count} records into table '{table_name}'")

        with self.get_session() as session:
            records = df.to_dicts()

            if not records:
                self.logger.warning(f"No records to upsert into '{table_name}'")
                return

            try:
                metadata = MetaData()
                table = Table(table_name, metadata, autoload_with=self.engine)

                stmt = insert(table).values(records)

                if conflict_key is None:
                    conflict_keys = [col.name for col in table.primary_key.columns]
                else:
                    conflict_keys = (
                        [conflict_key]
                        if isinstance(conflict_key, str)
                        else conflict_key
                    )

                update_cols = {
                    c: stmt.excluded[c] for c in df.columns if c not in conflict_keys
                }

                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=conflict_keys,
                    set_=update_cols,
                )

                session.exec(upsert_stmt)
                self.logger.info(
                    f"Successfully upserted {record_count} records into '{table_name}'"
                )
            except Exception as e:
                self.logger.error(f"Failed to upsert records into '{table_name}': {e}")
                raise

    def get_etag(self, endpoint: str) -> str | None:
        self.logger.debug(f"Retrieving ETag for endpoint: {endpoint}")

        try:
            with self.get_session() as session:
                existing_etag = session.get(ETag, endpoint)
                if existing_etag:
                    self.logger.debug(
                        f"Found ETag for endpoint '{endpoint}': {existing_etag.etag}"
                    )
                    return existing_etag.etag
                else:
                    self.logger.debug(f"No ETag found for endpoint '{endpoint}'")
                    return None
        except Exception as e:
            self.logger.error(f"Error retrieving ETag for endpoint '{endpoint}': {e}")
            raise

    def get_event_keys(self, active_only: bool = False) -> list[str]:
        self.logger.info(f"Retrieving event keys (active_only={active_only})")

        try:
            with self.get_session() as session:
                if not active_only:
                    query = select(Event.key)
                    keys = list(session.exec(query).all())
                    self.logger.info(f"Retrieved {len(keys)} event keys")
                    return keys

                query = select(Event)
                events = session.exec(query).all()

                buffer = timedelta(days=1, hours=2)
                active_keys = []

                for event in events:
                    event_tz = (
                        ZoneInfo(event.timezone)
                        if event.timezone
                        else ZoneInfo("UTC")  # If Timezone is missing, assume UTC
                    )
                    now_in_event_tz = datetime.now(event_tz).date()

                    event_start_with_buffer = event.start_date - buffer
                    event_end_with_buffer = event.end_date + buffer

                    if (
                        event_start_with_buffer
                        <= now_in_event_tz
                        <= event_end_with_buffer
                    ):
                        active_keys.append(event.key)

                self.logger.info(f"Retrieved {len(active_keys)} active event keys")
                return active_keys
        except Exception as e:
            self.logger.error(f"Error retrieving event keys: {e}")
            raise
