from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, String
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .alliance import Alliance
    from .match import Match
    from .ranking import Ranking, RankingEventInfo


class EventDistrict(SQLModel, table=True):
    __tablename__ = "event_districts"  # pyright: ignore[reportAssignmentType]

    key: str = Field(
        primary_key=True,
        description="District key (e.g., '2024ne').",
        regex=r"^\d{4}[a-z]+$",
    )

    year: int = Field(
        index=True,
        description="Competition year.",
        ge=1992,
    )
    abbreviation: str = Field(
        description="District abbreviation (e.g., 'ne', 'pnw').",
    )
    display_name: str = Field(
        description="District display name.",
    )

    events: list["Event"] = Relationship(back_populates="district")


class Event(SQLModel, table=True):
    __tablename__ = "events"  # pyright: ignore[reportAssignmentType]

    key: str = Field(
        primary_key=True,
        description="TBA event key (e.g., '2024pnw').",
        regex=r"^\d{4}[a-z0-9]+$",
    )

    district_key: str | None = Field(
        default=None,
        foreign_key="event_districts.key",
        index=True,
        description="District key if this is a district event.",
        regex=r"^\d{4}[a-z]+$",
    )
    parent_event_key: str | None = Field(
        default=None,
        foreign_key="events.key",
        index=True,
        description="Parent event key for division events.",
        regex=r"^\d{4}[a-z0-9]+$",
    )

    name: str = Field(
        description="Official event name.",
    )
    event_code: str = Field(
        index=True,
        description="FIRST event code.",
    )
    event_type: int = Field(
        description="Event type enum (Regional=0, District=1, etc.).",
        ge=0,
    )
    event_type_string: str = Field(
        description="Human-readable event type.",
    )
    year: int = Field(
        index=True,
        description="Competition year.",
        ge=1992,
    )
    start_date: date = Field(
        description="Event start date.",
    )
    end_date: date = Field(
        description="Event end date.",
    )

    week: int | None = Field(
        default=None,
        description="Competition week (zero-indexed, null for offseason).",
        ge=0,
    )
    short_name: str | None = Field(
        default=None,
        description="Event name without 'Regional'/'District' suffix.",
    )

    city: str | None = Field(default=None, description="Event city.")
    state_prov: str | None = Field(default=None, description="Event state or province.")
    country: str | None = Field(default=None, description="Event country.")
    postal_code: str | None = Field(default=None, description="Event postal code.")
    address: str | None = Field(default=None, description="Full venue address.")
    location_name: str | None = Field(default=None, description="Venue name.")
    timezone: str | None = Field(default=None, description="Event timezone.")
    lat: float | None = Field(
        default=None,
        description="Venue latitude.",
        ge=-90.0,
        le=90.0,
    )
    lng: float | None = Field(
        default=None,
        description="Venue longitude.",
        ge=-180.0,
        le=180.0,
    )

    website: str | None = Field(default=None, description="Official event website.")
    gmaps_place_id: str | None = Field(
        default=None, description="Google Maps Place ID."
    )
    gmaps_url: str | None = Field(default=None, description="Google Maps URL.")

    first_event_id: str | None = Field(
        default=None, description="FIRST internal event ID."
    )
    first_event_code: str | None = Field(
        default=None, description="FIRST public event code."
    )

    playoff_type: int | None = Field(
        default=None,
        description="Playoff format enum.",
        ge=0,
    )
    playoff_type_string: str | None = Field(
        default=None,
        description="Human-readable playoff format.",
    )

    division_keys: list[str] | None = Field(
        default=None,
        sa_column=Column(ARRAY(String)),
        description="Division event keys (for championship events).",
    )

    district: "EventDistrict" = Relationship(back_populates="events")
    parent_event: "Event" = Relationship(
        back_populates="division_events",
        sa_relationship_kwargs={
            "remote_side": "Event.key",
            "foreign_keys": "[Event.parent_event_key]",
        },
    )
    division_events: list["Event"] = Relationship(
        back_populates="parent_event",
        sa_relationship_kwargs={"foreign_keys": "[Event.parent_event_key]"},
    )
    matches: list["Match"] = Relationship(back_populates="event")
    rankings: list["Ranking"] = Relationship(back_populates="event")
    ranking_info: "RankingEventInfo" = Relationship(back_populates="event")
    alliances: list["Alliance"] = Relationship(back_populates="event")
