from typing import TYPE_CHECKING

from sqlalchemy import JSON
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .event import Event

from .ranking_info import RankingInfo


class EventRankingInfo(SQLModel, table=True):
    __tablename__ = "event_ranking_info"  # type: ignore[reportAssignmentType]

    event_key: str = Field(
        foreign_key="events.key",
        primary_key=True,
        index=True,
        description="TBA event key this ranking info describes.",
        regex=r"^\d{4}[a-z0-9]+$",
    )

    extra_stats_info: list[RankingInfo] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Metadata for TBA-generated values in the extra_stats array.",
    )

    sort_order_info: list[RankingInfo] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Metadata for year-specific values in the sort_orders array.",
    )

    event: "Event" = Relationship(back_populates="ranking_info")
