from typing import TYPE_CHECKING

from sqlalchemy import JSON
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .event import Event
    from .team import Team


class Ranking(SQLModel, table=True):
    __tablename__ = "rankings"  # type: ignore[reportAssignmentType]

    event_key: str = Field(
        foreign_key="events.key",
        primary_key=True,
        index=True,
        description="TBA event key for this ranking.",
        regex=r"^\d{4}[a-z0-9]+$",
    )

    team_key: str = Field(
        foreign_key="teams.key",
        primary_key=True,
        index=True,
        description="TBA team key for this ranking.",
        regex=r"^frc\d+$",
    )

    rank: int = Field(
        description="Team's rank at the event as provided by FIRST.",
        ge=1,
    )

    matches_played: int = Field(
        description="Number of qualification matches played.",
        ge=0,
    )

    qual_average: int | None = Field(
        default=None,
        description="Average qualification match score (year-specific, may be null).",
    )

    dq: int = Field(
        default=0,
        description="Number of disqualifications.",
        ge=0,
    )

    wins: int = Field(
        description="Number of wins.",
        ge=0,
    )

    losses: int = Field(
        description="Number of losses.",
        ge=0,
    )

    ties: int = Field(
        description="Number of ties.",
        ge=0,
    )

    extra_stats: list[int] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional year-specific statistics (see EventRankingInfo for field definitions).",
    )

    sort_orders: list[float] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Year-specific sort order values (see EventRankingInfo for field definitions).",
    )

    event: "Event" = Relationship(back_populates="rankings")
    team: "Team" = Relationship(back_populates="rankings")
