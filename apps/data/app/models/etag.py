from datetime import datetime

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel


class ETag(SQLModel, table=True):
    __tablename__ = "etags"  # pyright: ignore[reportAssignmentType]

    endpoint: str = Field(
        primary_key=True,
        description="The endpoint the etag is for",
    )

    etag: str = Field(
        description="Cached ETag for the endpoint",
    )

    created_at: datetime = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
        description="Timestamp when record was created",
    )

    updated_at: datetime = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        ),
        description="Timestamp when record was last updated",
    )
