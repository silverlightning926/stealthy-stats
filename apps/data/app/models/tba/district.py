from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .event import Event


class District(SQLModel, table=True):
    __tablename__ = "districts"  # pyright: ignore[reportAssignmentType]

    key: str = Field(
        primary_key=True,
        description="Key for this district, e.g. 2016ne.",
        regex=r"^\d{4}[a-z0-9]+$",
    )

    abbreviation: str = Field(
        description="The short identifier for the district.",
    )

    display_name: str = Field(
        description="The long name for the district.",
    )

    year: int = Field(
        index=True,
        description="Year this district participated.",
        ge=1992,
    )

    events: list["Event"] = Relationship(back_populates="district")
