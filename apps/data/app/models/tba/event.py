from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ARRAY, String
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .district import District
    from .match import Match
    from .ranking import Ranking


class Event(SQLModel, table=True):
    __tablename__ = "events"  # pyright: ignore[reportAssignmentType]

    key: str = Field(
        primary_key=True,
        description="TBA event key with the format yyyy[EVENT_CODE], where yyyy is the year, and EVENT_CODE is the event code of the event.",
        regex=r"^\d{4}[a-z0-9]+$",
    )

    name: str = Field(
        description="Official name of event on record either provided by FIRST or organizers of offseason event.",
    )

    event_code: str = Field(
        description="Event short code, as provided by FIRST.",
    )

    event_type: int = Field(
        description="Event Type, as defined here: https://github.com/the-blue-alliance/the-blue-alliance/blob/master/consts/event_type.py#L2",
        ge=0,
    )

    district_key: str | None = Field(
        default=None,
        foreign_key="districts.key",
        description="Key for the district this event is part of.",
    )

    city: str | None = Field(
        default=None,
        description="City, town, village, etc. the event is located in.",
    )

    state_prov: str | None = Field(
        default=None,
        description="State or Province the event is located in.",
    )

    country: str | None = Field(
        default=None,
        description="Country the event is located in.",
    )

    start_date: date = Field(description="Event start date in yyyy-mm-dd format.")

    end_date: date = Field(description="Event end date in yyyy-mm-dd format.")

    year: int = Field(
        index=True,
        description="Year the event data is for.",
        ge=1992,
    )

    short_name: str | None = Field(
        default=None,
        description="Same as name but doesn't include event specifiers, such as 'Regional' or 'District'. May be null.",
    )

    event_type_string: str = Field(
        description="Event Type, eg Regional, District, or Offseason.",
    )

    week: int | None = Field(
        default=None,
        description="Week of the event relative to the first official season event, zero-indexed. Only valid for Regionals, Districts, and District Championships. Null otherwise. (Eg. A season with a week 0 'preseason' event does not count, and week 1 events will show 0 here. Seasons with a week 0.5 regional event will show week 0 for those event(s) and week 1 for week 1 events and so on.)",
        ge=0,
    )

    address: str | None = Field(
        default=None,
        description="Address of the event's venue, if available.",
    )

    postal_code: str | None = Field(
        default=None,
        description="Postal code from the event address.",
    )

    gmaps_place_id: str | None = Field(
        default=None,
        description="Google Maps Place ID for the event address.",
    )

    gmaps_url: str | None = Field(
        default=None,
        description="Link to address location on Google Maps.",
    )

    lat: float | None = Field(
        default=None,
        description="Latitude for the event address.",
        ge=-90.0,
        le=90.0,
    )

    lng: float | None = Field(
        default=None,
        description="Longitude for the event address.",
        ge=-180.0,
        le=180.0,
    )

    location_name: str | None = Field(
        default=None,
        description="Name of the location at the address for the event, eg. Blue Alliance High School.",
    )

    timezone: str | None = Field(
        default=None,
        description="Timezone name.",
    )

    website: str | None = Field(
        default=None,
        description="The event's website, if any.",
    )

    first_event_id: str | None = Field(
        default=None,
        description="The FIRST internal Event ID, used to link to the event on the FRC webpage.",
    )

    first_event_code: str | None = Field(
        default=None,
        description="Public facing event code used by FIRST (on frc-events.firstinspires.org, for example)",
    )

    division_keys: list[str] | None = Field(
        default=None,
        sa_column=Column(ARRAY(String)),
        description="An array of event keys for the divisions at this event.",
    )

    parent_event_key: str | None = Field(
        default=None,
        foreign_key="events.key",
        description="The TBA Event key that represents the event's parent. Used to link back to the event from a division event. It is also the inverse relation of divison_keys.",
        regex=r"^\d{4}[a-z0-9]+$",
    )

    playoff_type: int | None = Field(
        default=None,
        description="Playoff Type, as defined under PlayoffType: https://github.com/the-blue-alliance/the-blue-alliance/blob/py3/src/backend/common/consts/playoff_type.py#L37, or null.",
        ge=0,
    )

    playoff_type_string: str | None = Field(
        default=None,
        description="String representation of the playoff_type, or null.",
    )

    district: Optional["District"] = Relationship(back_populates="events")
    matches: list["Match"] = Relationship(back_populates="event")
    rankings: list["Ranking"] = Relationship(back_populates="event")
