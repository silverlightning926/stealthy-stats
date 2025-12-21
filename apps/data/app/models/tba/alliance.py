from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKeyConstraint, func
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

    pick_order: int = Field(
        ge=1,
        description="Pick order (1=captain, 2=first pick).",
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

    alliance: "Alliance" = Relationship(back_populates="teams")
    event_team: "EventTeam" = Relationship(
        back_populates="alliance_participations",
        sa_relationship_kwargs={"overlaps": "alliance,teams"},
    )

    event: "Event" = Relationship(
        back_populates="alliance_teams",
        sa_relationship_kwargs={
            "viewonly": True,
            "primaryjoin": "AllianceTeam.event_key == Event.key",
            "foreign_keys": "[AllianceTeam.event_key]",
        },
    )
    team: "Team" = Relationship(
        back_populates="alliance_participations",
        sa_relationship_kwargs={
            "viewonly": True,
            "primaryjoin": "AllianceTeam.team_key == Team.key",
            "foreign_keys": "[AllianceTeam.team_key]",
        },
    )


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
    order: int | None = Field(
        default=None,
        ge=1,
        index=True,
        description="Numeric order for 'Alliance N' pattern, null for division names.",
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

    wins: int | None = Field(
        default=None,
        ge=0,
        description="Total playoff wins.",
    )
    losses: int | None = Field(
        default=None,
        ge=0,
        description="Total playoff losses.",
    )
    ties: int | None = Field(
        default=None,
        ge=0,
        description="Total playoff ties.",
    )

    current_level_wins: int | None = Field(
        default=None,
        ge=0,
        description="Wins at current playoff level.",
    )
    current_level_losses: int | None = Field(
        default=None,
        ge=0,
        description="Losses at current playoff level.",
    )
    current_level_ties: int | None = Field(
        default=None,
        ge=0,
        description="Ties at current playoff level.",
    )

    playoff_type: int | None = Field(
        default=None,
        ge=0,
        description="Playoff type enum.",
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
        ge=1,
        description="Round robin ranking.",
    )
    advanced_to_round_robin_finals: bool | None = Field(
        default=None,
        description="Whether alliance advanced to round robin finals.",
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

    event: "Event" = Relationship(back_populates="alliances")
    teams: list["AllianceTeam"] = Relationship(
        back_populates="alliance",
        sa_relationship_kwargs={"overlaps": "event_team,alliance_participations"},
    )

    team_backup_in: "Team" = Relationship(
        back_populates="alliances_backup_in",
        sa_relationship_kwargs={"foreign_keys": "[Alliance.backup_in]"},
    )
    team_backup_out: "Team" = Relationship(
        back_populates="alliances_backup_out",
        sa_relationship_kwargs={"foreign_keys": "[Alliance.backup_out]"},
    )
