from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, Column, String
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .event import Event
    from .team import Team


class Alliance(SQLModel, table=True):
    __tablename__ = "alliances"  # type: ignore[reportAssignmentType]

    event_key: str = Field(
        foreign_key="events.key",
        primary_key=True,
        index=True,
        description="TBA event key this alliance belongs to.",
        regex=r"^\d{4}[a-z0-9]+$",
    )

    name: str = Field(
        primary_key=True,
        description="Alliance name/identifier (e.g. 'Alliance 1', 'Alliance 2').",
    )

    picks: list[str] = Field(
        sa_column=Column(ARRAY(String)),
        description="Team keys picked for the alliance. First pick is the captain.",
    )

    declines: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String)),
        description="Team keys that declined to join this alliance.",
    )

    backup_in: str | None = Field(
        default=None,
        foreign_key="teams.key",
        index=True,
        description="Team key that was called in as a backup replacement.",
        regex=r"^frc\d+$",
    )

    backup_out: str | None = Field(
        default=None,
        foreign_key="teams.key",
        index=True,
        description="Team key that was replaced by the backup team.",
        regex=r"^frc\d+$",
    )

    playoff_average: float | None = Field(
        default=None,
        description="Average match score during playoffs (year-specific, may be null).",
    )

    playoff_type: int | None = Field(
        default=None,
        description="Playoff type identifier (may be null).",
        ge=0,
    )

    status: str | None = Field(
        default=None,
        description="Alliance status in playoffs.",
        regex=r"^(eliminated|playing|won)$",
    )

    wins: int | None = Field(
        default=None,
        description="Total playoff wins.",
        ge=0,
    )

    losses: int | None = Field(
        default=None,
        description="Total playoff losses.",
        ge=0,
    )

    ties: int | None = Field(
        default=None,
        description="Total playoff ties.",
        ge=0,
    )

    level: str | None = Field(
        default=None,
        description="Current playoff level: qm/ef/qf/sf/f.",
        regex=r"^(qm|ef|qf|sf|f)$",
    )

    current_level_wins: int | None = Field(
        default=None,
        description="Wins at the current playoff level.",
        ge=0,
    )

    current_level_losses: int | None = Field(
        default=None,
        description="Losses at the current playoff level.",
        ge=0,
    )

    current_level_ties: int | None = Field(
        default=None,
        description="Ties at the current playoff level.",
        ge=0,
    )

    advanced_to_round_robin_finals: bool | None = Field(
        default=None,
        description="Whether the alliance advanced to round robin finals.",
    )

    double_elim_round: str | None = Field(
        default=None,
        description="Current round in double elimination format.",
        regex=r"^(Finals|Round 1|Round 2|Round 3|Round 4|Round 5)$",
    )

    round_robin_rank: int | None = Field(
        default=None,
        description="Rank in round robin play.",
        ge=1,
    )

    event: "Event" = Relationship(back_populates="alliances")

    team_backup_in: "Team" = Relationship(
        back_populates="alliances_backup_in",
        sa_relationship_kwargs={
            "foreign_keys": "[Alliance.backup_in]",
            "primaryjoin": "Alliance.backup_in == Team.key",
        },
    )

    team_backup_out: "Team" = Relationship(
        back_populates="alliances_backup_out",
        sa_relationship_kwargs={
            "foreign_keys": "[Alliance.backup_out]",
            "primaryjoin": "Alliance.backup_out == Team.key",
        },
    )
