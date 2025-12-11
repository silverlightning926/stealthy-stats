from typing import TYPE_CHECKING

from sqlalchemy import JSON
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .event import Event

from .ranking_info import RankingInfo


class EventRankingInfo(SQLModel, table=True):
    __tablename__ = "event_ranking_info"  # pyright: ignore[reportAssignmentType]

    event_key: str = Field(
        foreign_key="events.key",
        primary_key=True,
        description="TBA event key this ranking info belongs to.",
        regex=r"^\d{4}[a-z0-9]+$",
    )

    extra_stats_info: list[RankingInfo] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="List of special TBA-generated values provided in the extra_stats array for each ranking item.",
    )

    sort_order_info: list[RankingInfo] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="List of year-specific values provided in the sort_orders array for each team ranking.",
    )

    event: "Event" = Relationship(back_populates="ranking_info")
