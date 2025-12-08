from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .event import Event
    from .match_alliance import MatchAlliance


class Match(SQLModel, table=True):
    __tablename__ = "matches"  # pyright: ignore[reportAssignmentType]

    key: str = Field(
        primary_key=True,
        description="TBA match key with the format yyyy[EVENT_CODE]_[COMP_LEVEL]m[MATCH_NUMBER], where yyyy is the year, and EVENT_CODE is the event code of the event, COMP_LEVEL is (qm, ef, qf, sf, f), and MATCH_NUMBER is the match number in the competition level.",
        regex=r"^\d{4}[a-z0-9]+_(qm|ef|qf|sf|f)\d*m\d+$",
    )

    comp_level: str = Field(
        description="The competition level the match was played at.",
        regex=r"^(qm|ef|qf|sf|f)$",
    )

    set_number: int = Field(
        description="The set number in a series of matches where more than one match is required in the match series.",
        ge=1,
    )

    match_number: int = Field(
        description="The match number of the match in the competition level.",
        ge=1,
    )

    winning_alliance: str = Field(
        default="",
        description="The color (red/blue) of the winning alliance. Will contain an empty string in the event of no winner, or a tie.",
        regex=r"^(red|blue|)$",
    )

    event_key: str = Field(
        foreign_key="events.key",
        description="Event key of the event the match was played at.",
        regex=r"^\d{4}[a-z0-9]+$",
    )

    time: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Scheduled match time, as taken from the published schedule.",
    )

    actual_time: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Actual match start time.",
    )

    predicted_time: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="TBA predicted match start time.",
    )

    post_result_time: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Time when the match result was posted.",
    )

    event: "Event" = Relationship(back_populates="matches")
    alliances: list["MatchAlliance"] = Relationship(back_populates="match")
