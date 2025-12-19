from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Column, DateTime, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .event import Event
    from .team import Team


class RankingSortOrderInfo(SQLModel):
    name: str = Field(
        description="Name of the ranking field.",
    )
    precision: int = Field(
        ge=0,
        description="Number of decimal digits for this field.",
    )


class RankingEventInfo(SQLModel, table=True):
    __tablename__ = "ranking_event_infos"  # pyright: ignore[reportAssignmentType]

    event_key: str = Field(
        primary_key=True,
        foreign_key="events.key",
        description="TBA event key.",
        regex=r"^\d{4}[a-z0-9]+$",
    )

    extra_stats_info: list[RankingSortOrderInfo] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Metadata for TBA-computed extra_stats values.",
    )
    sort_order_info: list[RankingSortOrderInfo] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Metadata for year-specific sort_orders values.",
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

    event: "Event" = Relationship(
        back_populates="ranking_info",
    )


class Ranking(SQLModel, table=True):
    __tablename__ = "rankings"  # pyright: ignore[reportAssignmentType]

    event_key: str = Field(
        primary_key=True,
        foreign_key="events.key",
        index=True,
        description="TBA event key.",
        regex=r"^\d{4}[a-z0-9]+$",
    )
    team_key: str = Field(
        primary_key=True,
        foreign_key="teams.key",
        index=True,
        description="TBA team key (e.g., 'frc254').",
        regex=r"^frc\d+$",
    )

    rank: int = Field(
        ge=1,
        description="Team's rank at this event.",
    )
    matches_played: int = Field(
        ge=0,
        description="Number of qualification matches played.",
    )

    wins: int | None = Field(
        default=None,
        ge=0,
        description="Number of qualification wins.",
    )
    losses: int | None = Field(
        default=None,
        ge=0,
        description="Number of qualification losses.",
    )
    ties: int | None = Field(
        default=None,
        ge=0,
        description="Number of qualification ties.",
    )

    dq: int = Field(
        default=0,
        ge=0,
        description="Number of disqualifications.",
    )
    qual_average: float | None = Field(
        default=None,
        description="Average qualification match score (year-specific).",
    )
    extra_stats: list[float] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="TBA-computed statistics (see RankingEventInfo.extra_stats_info).",
    )
    sort_orders: list[float] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Year-specific ranking values (see RankingEventInfo.sort_order_info).",
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

    event: "Event" = Relationship(
        back_populates="rankings",
    )
    team: "Team" = Relationship(
        back_populates="rankings",
    )
