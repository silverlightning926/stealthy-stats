from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Column, DateTime, ForeignKeyConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .event import Event
    from .team import Team


class MatchAllianceTeam(SQLModel, table=True):
    __tablename__ = "match_alliance_teams"  # type: ignore[reportAssignmentType]

    __table_args__ = (
        ForeignKeyConstraint(
            ["match_key", "alliance_color"],
            ["match_alliances.match_key", "match_alliances.alliance_color"],
        ),
    )

    match_key: str = Field(
        primary_key=True,
        index=True,
        description="TBA match key.",
    )

    alliance_color: str = Field(
        primary_key=True,
        description="Alliance color: 'red' or 'blue'.",
        regex=r"^(red|blue)$",
    )

    team_key: str = Field(
        foreign_key="teams.key",
        primary_key=True,
        index=True,
        description="TBA team key (e.g. 'frc254').",
        regex=r"^frc\d+$",
    )

    is_surrogate: bool = Field(
        default=False,
        description="Whether this team is a surrogate.",
    )

    is_dq: bool = Field(
        default=False,
        description="Whether this team was disqualified.",
    )

    match: "Match" = Relationship(back_populates="alliance_teams")
    alliance: "MatchAlliance" = Relationship(back_populates="teams")
    team: "Team" = Relationship(back_populates="match_participations")


class MatchAlliance(SQLModel, table=True):
    __tablename__ = "match_alliances"  # type: ignore[reportAssignmentType]

    match_key: str = Field(
        foreign_key="matches.key",
        primary_key=True,
        index=True,
        description="TBA match key this alliance belongs to.",
    )

    alliance_color: str = Field(
        primary_key=True,
        description="Alliance color: 'red' or 'blue'.",
        regex=r"^(red|blue)$",
    )

    score: int = Field(
        description="Alliance score (-1 for unplayed matches).",
    )

    score_breakdown: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Detailed score breakdown (auto, teleop, etc). Year-specific structure.",
    )

    match: "Match" = Relationship(back_populates="alliances")
    teams: list["MatchAllianceTeam"] = Relationship(back_populates="alliance")


class Match(SQLModel, table=True):
    __tablename__ = "matches"  # type: ignore[reportAssignmentType]

    key: str = Field(
        primary_key=True,
        description="TBA match key: yyyy[EVENT_CODE]_[COMP_LEVEL]m[MATCH_NUMBER], e.g. '2024pnw_qm1'.",
        regex=r"^\d{4}[a-z0-9]+_(qm|ef|qf|sf|f)\d*m\d+$",
    )

    event_key: str = Field(
        foreign_key="events.key",
        index=True,
        description="Event key where this match was played.",
        regex=r"^\d{4}[a-z0-9]+$",
    )

    comp_level: str = Field(
        index=True,
        description="Competition level: qm (quals), ef/qf/sf/f (playoffs).",
        regex=r"^(qm|ef|qf|sf|f)$",
    )

    set_number: int = Field(
        description="Set number in playoff series (1 for single-match rounds).",
        ge=1,
    )

    match_number: int = Field(
        description="Match number within the competition level.",
        ge=1,
    )

    winning_alliance: str = Field(
        default="",
        description="Winning alliance color ('red', 'blue', or empty string for tie/unplayed).",
        regex=r"^(red|blue|)$",
    )

    time: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Scheduled match time from published schedule.",
    )

    actual_time: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Actual match start time.",
    )

    predicted_time: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="TBA-predicted match start time.",
    )

    post_result_time: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Time when match results were posted.",
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
