from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .event import Event


class District(SQLModel, table=True):
    __tablename__ = "districts"  # type: ignore[reportAssignmentType]

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
