from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, String
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .alliance import Alliance
    from .match import Match
    from .ranking import EventRankingInfo, Ranking


class EventDistrict(SQLModel, table=True):
    __tablename__ = "event_districts"  # type: ignore[reportAssignmentType]

    key: str = Field(
        primary_key=True,
        description="District key with format yyyy[DISTRICT_CODE], e.g. '2016ne'.",
        regex=r"^\d{4}[a-z0-9]+$",
    )

    abbreviation: str = Field(
        description="Short identifier for the district (e.g. 'ne', 'pnw').",
    )

    display_name: str = Field(
        description="Full display name for the district.",
    )

    year: int = Field(
        index=True,
        description="Competition year for this district.",
        ge=1992,
    )

    events: list["Event"] = Relationship(back_populates="district")


class Event(SQLModel, table=True):
    __tablename__ = "events"  # type: ignore[reportAssignmentType]

    key: str = Field(
        primary_key=True,
        description="TBA event key with format yyyy[EVENT_CODE], e.g. '2024pnw'.",
        regex=r"^\d{4}[a-z0-9]+$",
    )

    name: str = Field(
        description="Official event name from FIRST or offseason organizers.",
    )

    event_code: str = Field(
        index=True,
        description="Event short code provided by FIRST.",
    )

    event_type: int = Field(
        description="Event type (Regional=0, District=1, etc). See TBA event_type.py.",
        ge=0,
    )

    event_type_string: str = Field(
        description="Human-readable event type (Regional, District, Offseason, etc).",
    )

    year: int = Field(
        index=True,
        description="Competition year for this event.",
        ge=1992,
    )

    week: int | None = Field(
        default=None,
        description="Week relative to first official season event (zero-indexed). Null for offseason.",
        ge=0,
    )

    start_date: date = Field(
        description="Event start date.",
    )

    end_date: date = Field(
        description="Event end date.",
    )

    city: str | None = Field(
        default=None,
        description="City where the event is located.",
    )

    state_prov: str | None = Field(
        default=None,
        description="State or province where the event is located.",
    )

    country: str | None = Field(
        default=None,
        description="Country where the event is located.",
    )

    postal_code: str | None = Field(
        default=None,
        description="Postal code for the event location.",
    )

    address: str | None = Field(
        default=None,
        description="Full address of the event venue.",
    )

    location_name: str | None = Field(
        default=None,
        description="Venue name (e.g. 'Blue Alliance High School').",
    )

    lat: float | None = Field(
        default=None,
        description="Latitude of the event location.",
        ge=-90.0,
        le=90.0,
    )

    lng: float | None = Field(
        default=None,
        description="Longitude of the event location.",
        ge=-180.0,
        le=180.0,
    )

    timezone: str | None = Field(
        default=None,
        description="Timezone name for the event location.",
    )

    short_name: str | None = Field(
        default=None,
        description="Event name without specifiers like 'Regional' or 'District'.",
    )

    website: str | None = Field(
        default=None,
        description="Official event website URL.",
    )

    gmaps_place_id: str | None = Field(
        default=None,
        description="Google Maps Place ID for the event address.",
    )

    gmaps_url: str | None = Field(
        default=None,
        description="Google Maps URL for the event location.",
    )

    first_event_id: str | None = Field(
        default=None,
        description="FIRST internal event ID for linking to FRC webpage.",
    )

    first_event_code: str | None = Field(
        default=None,
        description="Public-facing event code used by FIRST.",
    )

    playoff_type: int | None = Field(
        default=None,
        description="Playoff type enum. See TBA playoff_type.py.",
        ge=0,
    )

    playoff_type_string: str | None = Field(
        default=None,
        description="Human-readable playoff type.",
    )

    district_key: str | None = Field(
        default=None,
        foreign_key="event_districts.key",
        index=True,
        description="District key if this is a district event.",
    )

    parent_event_key: str | None = Field(
        default=None,
        foreign_key="events.key",
        index=True,
        description="Parent event key for division events (links division to championship).",
        regex=r"^\d{4}[a-z0-9]+$",
    )

    division_keys: list[str] | None = Field(
        default=None,
        sa_column=Column(ARRAY(String)),
        description="Event keys for divisions at this event (for championship events).",
    )

    district: "EventDistrict" = Relationship(back_populates="events")

    parent_event: "Event" = Relationship(
        back_populates="division_events",
        sa_relationship_kwargs={
            "remote_side": "[Event.key]",
            "foreign_keys": "[Event.parent_event_key]",
        },
    )

    division_events: list["Event"] = Relationship(
        back_populates="parent_event",
        sa_relationship_kwargs={
            "foreign_keys": "[Event.parent_event_key]",
        },
    )

    matches: list["Match"] = Relationship(back_populates="event")
    rankings: list["Ranking"] = Relationship(back_populates="event")
    ranking_info: "EventRankingInfo" = Relationship(back_populates="event")
    alliances: list["Alliance"] = Relationship(back_populates="event")
