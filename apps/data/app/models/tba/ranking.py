from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .event import Event
    from .team import Team


class Ranking(SQLModel, table=True):
    __tablename__ = "rankings"  # pyright: ignore[reportAssignmentType]

    event_key: str = Field(
        foreign_key="events.key",
        primary_key=True,
        description="TBA event key this ranking belongs to.",
        regex=r"^\d{4}[a-z0-9]+$",
    )

    team_key: str = Field(
        foreign_key="teams.key",
        primary_key=True,
        description="TBA team key for this ranking.",
        regex=r"^frc\d+$",
    )

    rank: int = Field(
        description="The team's rank at the event as provided by FIRST.",
        ge=1,
    )

    matches_played: int = Field(
        description="Number of matches played by this team.",
        ge=0,
    )

    qual_average: int | None = Field(
        default=None,
        description="The average match score during qualifications. Year specific. May be null if not relevant for a given year.",
    )

    dq: int = Field(
        default=0,
        description="Number of times disqualified.",
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

    event: "Event" = Relationship(back_populates="rankings")
    team: "Team" = Relationship(back_populates="rankings")
