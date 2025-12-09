from contextlib import contextmanager
from datetime import datetime, timedelta

import polars as pl
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import MetaData, Table
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import ETag  # noqa: F401
from app.models.tba import District, Event, Team  # noqa: F401


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
        )

        SQLModel.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self):
        session = Session(self.engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def upsert(self, df: pl.DataFrame, table_name: str, conflict_key: str):
        with self.get_session() as session:
            records = df.to_dicts()

            if not records:
                return

            metadata = MetaData()
            table = Table(table_name, metadata, autoload_with=self.engine)

            stmt = insert(table).values(records)

            update_cols = {c: stmt.excluded[c] for c in df.columns if c != conflict_key}

            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=[conflict_key],
                set_=update_cols,
            )

            session.exec(upsert_stmt)

    def get_etag(self, endpoint: str) -> str | None:
        with self.get_session() as session:
            existing_etag = session.get(ETag, endpoint)
            return existing_etag.etag if existing_etag else None

    def get_event_keys(self, active_only: bool = False) -> list[str]:
        with self.get_session() as session:
            query = select(Event.key)

            if active_only:
                now = datetime.now()
                buffer = timedelta(days=1)
                query = query.where(
                    Event.start_date <= now + buffer,
                    Event.end_date >= now - buffer,
                )

            return list(session.exec(query).all())
