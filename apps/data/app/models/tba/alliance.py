from typing import TYPE_CHECKING

from sqlalchemy import ForeignKeyConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .event import Event, EventTeam
    from .team import Team


class AllianceTeam(SQLModel, table=True):
    __tablename__ = "alliance_teams"  # pyright: ignore[reportAssignmentType]

    __table_args__ = (
        ForeignKeyConstraint(
            ["event_key", "alliance_name"],
            ["alliances.event_key", "alliances.name"],
        ),
        ForeignKeyConstraint(
            ["event_key", "team_key"],
            ["event_teams.event_key", "event_teams.team_key"],
        ),
    )

    event_key: str = Field(
        primary_key=True,
        index=True,
        description="TBA event key.",
        regex=r"^\d{4}[a-z0-9]+$",
    )
    alliance_name: str = Field(
        primary_key=True,
        description="Alliance identifier (e.g., 'Alliance 1').",
    )
    team_key: str = Field(
        primary_key=True,
        index=True,
        description="TBA team key (e.g., 'frc254').",
        regex=r"^frc\d+$",
    )

    pick_order: int | None = Field(
        default=None,
        description="Pick order (1=captain, 2=first pick). Null if declined.",
        ge=1,
    )

    alliance: "Alliance" = Relationship(back_populates="teams")
    event_team: "EventTeam" = Relationship(back_populates="alliance_participations")


class Alliance(SQLModel, table=True):
    __tablename__ = "alliances"  # pyright: ignore[reportAssignmentType]

    event_key: str = Field(
        primary_key=True,
        foreign_key="events.key",
        index=True,
        description="TBA event key.",
        regex=r"^\d{4}[a-z0-9]+$",
    )
    name: str = Field(
        primary_key=True,
        description="Alliance identifier (e.g., 'Alliance 1').",
    )

    backup_in: str | None = Field(
        default=None,
        foreign_key="teams.key",
        index=True,
        description="Team called in as backup.",
        regex=r"^frc\d+$",
    )
    backup_out: str | None = Field(
        default=None,
        foreign_key="teams.key",
        index=True,
        description="Team replaced by backup.",
        regex=r"^frc\d+$",
    )

    status: str | None = Field(
        default=None,
        description="Alliance playoff status.",
        regex=r"^(eliminated|playing|won)$",
    )
    level: str | None = Field(
        default=None,
        description="Current playoff level.",
        regex=r"^(qm|ef|qf|sf|f)$",
    )

    wins: int | None = Field(default=None, description="Total playoff wins.", ge=0)
    losses: int | None = Field(default=None, description="Total playoff losses.", ge=0)
    ties: int | None = Field(default=None, description="Total playoff ties.", ge=0)
    current_level_wins: int | None = Field(
        default=None,
        description="Wins at current playoff level.",
        ge=0,
    )
    current_level_losses: int | None = Field(
        default=None,
        description="Losses at current playoff level.",
        ge=0,
    )
    current_level_ties: int | None = Field(
        default=None,
        description="Ties at current playoff level.",
        ge=0,
    )

    playoff_type: int | None = Field(
        default=None, description="Playoff type enum.", ge=0
    )
    playoff_average: float | None = Field(
        default=None,
        description="Average playoff match score.",
    )
    double_elim_round: str | None = Field(
        default=None,
        description="Current double elimination round.",
        regex=r"^(Finals|Round [1-5])$",
    )
    round_robin_rank: int | None = Field(
        default=None,
        description="Round robin ranking.",
        ge=1,
    )
    advanced_to_round_robin_finals: bool | None = Field(
        default=None,
        description="Whether alliance advanced to round robin finals.",
    )

    event: "Event" = Relationship(back_populates="alliances")
    teams: list["AllianceTeam"] = Relationship(back_populates="alliance")
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
