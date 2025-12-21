from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .alliance import Alliance, AllianceTeam
    from .event import EventTeam
    from .match import MatchAllianceTeam
    from .ranking import Ranking


class Team(SQLModel, table=True):
    __tablename__ = "teams"  # pyright: ignore[reportAssignmentType]

    key: str = Field(
        primary_key=True,
        description="TBA team key (e.g., 'frc254').",
        regex=r"^frc\d+$",
    )

    team_number: int = Field(
        index=True,
        gt=0,
        description="Official FIRST team number.",
    )
    nickname: str = Field(
        description="Team nickname.",
    )
    name: str = Field(
        description="Official registered team name.",
    )

    school_name: str | None = Field(
        default=None,
        description="School or organization name.",
    )
    city: str | None = Field(
        default=None,
        description="Team city.",
    )
    state_prov: str | None = Field(
        default=None,
        description="Team state or province.",
    )
    country: str | None = Field(
        default=None,
        description="Team country.",
    )
    postal_code: str | None = Field(
        default=None,
        description="Team postal code.",
    )
    website: str | None = Field(
        default=None,
        description="Team website URL.",
    )
    rookie_year: int | None = Field(
        default=None,
        index=True,
        ge=1992,
        description="Year the team first competed.",
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

    event_participations: list["EventTeam"] = Relationship(back_populates="team")

    match_participations: list["MatchAllianceTeam"] = Relationship(
        back_populates="team",
        sa_relationship_kwargs={
            "viewonly": True,
            "primaryjoin": "Team.key == MatchAllianceTeam.team_key",
            "foreign_keys": "[MatchAllianceTeam.team_key]",
        },
    )
    alliance_participations: list["AllianceTeam"] = Relationship(
        back_populates="team",
        sa_relationship_kwargs={
            "viewonly": True,
            "primaryjoin": "Team.key == AllianceTeam.team_key",
            "foreign_keys": "[AllianceTeam.team_key]",
        },
    )
    rankings: list["Ranking"] = Relationship(
        back_populates="team",
        sa_relationship_kwargs={
            "viewonly": True,
            "primaryjoin": "Team.key == Ranking.team_key",
            "foreign_keys": "[Ranking.team_key]",
        },
    )

    alliances_backup_in: list["Alliance"] = Relationship(
        back_populates="team_backup_in",
        sa_relationship_kwargs={"foreign_keys": "[Alliance.backup_in]"},
    )
    alliances_backup_out: list["Alliance"] = Relationship(
        back_populates="team_backup_out",
        sa_relationship_kwargs={"foreign_keys": "[Alliance.backup_out]"},
    )
