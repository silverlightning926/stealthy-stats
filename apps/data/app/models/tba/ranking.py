from typing import TYPE_CHECKING

from sqlalchemy import JSON
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .event import Event
    from .team import Team


class RankingSortOrderInfo(SQLModel):
    name: str = Field(description="Name of the ranking field.")
    precision: int = Field(
        description="Number of decimal digits for this field.",
        ge=0,
    )


class RankingEventInfo(SQLModel, table=True):
    __tablename__ = "event_ranking_info"  # pyright: ignore[reportAssignmentType]

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

    event: "Event" = Relationship(back_populates="ranking_info")


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
        description="Team's rank at this event.",
        ge=1,
    )
    matches_played: int = Field(
        description="Number of qualification matches played.",
        ge=0,
    )
    wins: int = Field(
        description="Number of qualification wins.",
        ge=0,
    )
    losses: int = Field(
        description="Number of qualification losses.",
        ge=0,
    )
    ties: int = Field(
        description="Number of qualification ties.",
        ge=0,
    )

    dq: int = Field(
        default=0,
        description="Number of disqualifications.",
        ge=0,
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

    event: "Event" = Relationship(back_populates="rankings")
    team: "Team" = Relationship(back_populates="rankings")
