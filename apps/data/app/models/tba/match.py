from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ARRAY, JSON, Column, DateTime, String
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .event import Event


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

    team_keys: list[str] = Field(
        sa_column=Column(ARRAY(String)),
        description="TBA team keys (e.g. 'frc254') for teams on this alliance.",
    )

    surrogate_team_keys: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String)),
        description="TBA team keys of surrogate teams.",
    )

    dq_team_keys: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String)),
        description="TBA team keys of disqualified teams.",
    )

    score_breakdown: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Detailed score breakdown (auto, teleop, etc). Year-specific structure.",
    )

    match: "Match" = Relationship(back_populates="alliances")


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
