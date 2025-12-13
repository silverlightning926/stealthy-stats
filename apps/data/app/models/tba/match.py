from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Column, DateTime, ForeignKeyConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .event import Event, EventTeam


class MatchAllianceTeam(SQLModel, table=True):
    __tablename__ = "match_alliance_teams"  # pyright: ignore[reportAssignmentType]

    __table_args__ = (
        ForeignKeyConstraint(
            ["match_key", "alliance_color"],
            ["match_alliances.match_key", "match_alliances.alliance_color"],
        ),
        ForeignKeyConstraint(
            ["event_key", "team_key"],
            ["event_teams.event_key", "event_teams.team_key"],
        ),
    )

    match_key: str = Field(
        primary_key=True,
        foreign_key="matches.key",
        index=True,
        description="TBA match key.",
        regex=r"^\d{4}[a-z0-9]+_(qm|ef|qf|sf|f)\d*m\d+$",
    )
    alliance_color: str = Field(
        primary_key=True,
        description="Alliance color.",
        regex=r"^(red|blue)$",
    )
    team_key: str = Field(
        primary_key=True,
        index=True,
        description="TBA team key (e.g., 'frc254').",
        regex=r"^frc\d+$",
    )

    event_key: str = Field(
        index=True,
        description="TBA event key (denormalized from match).",
        regex=r"^\d{4}[a-z0-9]+$",
    )

    is_surrogate: bool = Field(
        default=False,
        description="Whether team is a surrogate.",
    )
    is_dq: bool = Field(
        default=False,
        description="Whether team was disqualified.",
    )

    match: "Match" = Relationship(back_populates="alliance_teams")
    alliance: "MatchAlliance" = Relationship(back_populates="teams")
    event_team: "EventTeam" = Relationship(back_populates="match_participations")


class MatchAlliance(SQLModel, table=True):
    __tablename__ = "match_alliances"  # pyright: ignore[reportAssignmentType]

    match_key: str = Field(
        primary_key=True,
        foreign_key="matches.key",
        index=True,
        description="TBA match key.",
        regex=r"^\d{4}[a-z0-9]+_(qm|ef|qf|sf|f)\d*m\d+$",
    )
    alliance_color: str = Field(
        primary_key=True,
        description="Alliance color.",
        regex=r"^(red|blue)$",
    )

    score: int = Field(
        description="Alliance score (-1 if unplayed).",
    )

    score_breakdown: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Detailed year-specific score breakdown.",
    )

    match: "Match" = Relationship(back_populates="alliances")
    teams: list["MatchAllianceTeam"] = Relationship(back_populates="alliance")


class Match(SQLModel, table=True):
    __tablename__ = "matches"  # pyright: ignore[reportAssignmentType]

    key: str = Field(
        primary_key=True,
        description="TBA match key (e.g., '2024pnw_qm1').",
        regex=r"^\d{4}[a-z0-9]+_(qm|ef|qf|sf|f)\d*m\d+$",
    )

    event_key: str = Field(
        foreign_key="events.key",
        index=True,
        description="TBA event key.",
        regex=r"^\d{4}[a-z0-9]+$",
    )

    comp_level: str = Field(
        index=True,
        description="Competition level (qm, ef, qf, sf, f).",
        regex=r"^(qm|ef|qf|sf|f)$",
    )
    set_number: int = Field(
        description="Set number in playoff series.",
        ge=1,
    )
    match_number: int = Field(
        description="Match number within competition level.",
        ge=1,
    )

    winning_alliance: str = Field(
        default="",
        description="Winning alliance color (empty if tie/unplayed).",
        regex=r"^(red|blue|)$",
    )

    time: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Scheduled match time.",
    )
    actual_time: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Actual match start time.",
    )
    predicted_time: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="TBA predicted match time.",
    )
    post_result_time: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Time when results were posted.",
    )

    event: "Event" = Relationship(back_populates="matches")
    alliances: list["MatchAlliance"] = Relationship(back_populates="match")
    alliance_teams: list["MatchAllianceTeam"] = Relationship(
        back_populates="match",
        sa_relationship_kwargs={
            "foreign_keys": "[MatchAllianceTeam.match_key]",
            "primaryjoin": "Match.key == MatchAllianceTeam.match_key",
        },
    )
