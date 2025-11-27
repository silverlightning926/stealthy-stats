from contextlib import contextmanager

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlmodel import Session, SQLModel, create_engine


class _DBConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_url: str = Field(..., min_length=1, validation_alias="DATABASE_URL")


class DBService:
    def __init__(self):
        self.config = _DBConfig()  # pyright: ignore[reportCallIssue]

        self.engine = create_engine(
            url=self.config.db_url,
        )

    def create_tables(self):
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

    def add(self, model: SQLModel):
        with self.get_session() as session:
            session.add(model)

    def add_all(self, models: list[SQLModel]):
        with self.get_session() as session:
            session.add_all(models)
