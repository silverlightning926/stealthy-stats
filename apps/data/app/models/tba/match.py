from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .event import Event
    from .match_alliance import MatchAlliance


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
