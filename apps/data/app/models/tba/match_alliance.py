from typing import TYPE_CHECKING, Any

from sqlalchemy import ARRAY, JSON, Column, String
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .match import Match


class MatchAlliance(SQLModel, table=True):
    __tablename__ = "match_alliances"  # pyright: ignore[reportAssignmentType]

    match_key: str = Field(
        foreign_key="matches.key",
        primary_key=True,
        description="TBA match key this alliance belongs to.",
    )

    alliance_color: str = Field(
        primary_key=True,
        description="Alliance color: 'red' or 'blue'.",
        regex=r"^(red|blue)$",
    )

    score: int = Field(
        description="Score for this alliance. Will be -1 for an unplayed match.",
    )

    team_keys: list[str] = Field(
        sa_column=Column(ARRAY(String)),
        description="TBA Team keys (eg frc254) for teams on this alliance.",
    )

    surrogate_team_keys: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String)),
        description="TBA team keys (eg frc254) of any teams playing as a surrogate.",
    )

    dq_team_keys: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String)),
        description="TBA team keys (eg frc254) of any disqualified teams.",
    )

    score_breakdown: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Score breakdown for auto, teleop, etc. points. Varies from year to year. May be null.",
    )

    match: "Match" = Relationship(back_populates="alliances")
