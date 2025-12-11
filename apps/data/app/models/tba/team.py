from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .ranking import Ranking


class Team(SQLModel, table=True):
    __tablename__ = "teams"  # pyright: ignore[reportAssignmentType]

    key: str = Field(
        primary_key=True,
        description="TBA team key with the format frcXXXX with XXXX representing the team number",
        regex=r"^frc\d+$",
    )
    team_number: int = Field(
        description="Official team number issued by FIRST",
        gt=0,
    )
    nickname: str = Field(description="Team nickname provided by FIRST")
    name: str = Field(description="Official long name registered with FIRST")

    school_name: str | None = Field(
        default=None,
        description="Name of team school or affiliated group registered with FIRST",
    )
    city: str | None = Field(
        default=None,
        description="City of team derived from parsing the address registered with FIRST",
    )
    state_prov: str | None = Field(
        default=None,
        description="State of team derived from parsing the address registered with FIRST",
    )
    country: str | None = Field(
        default=None,
        description="Country of team derived from parsing the address registered with FIRST",
    )
    postal_code: str | None = Field(
        default=None,
        description="Postal code from the team address",
    )

    website: str | None = Field(
        default=None,
        description="Official website associated with the team",
    )

    rookie_year: int | None = Field(
        default=None,
        description="First year the team officially competed",
        ge=1992,
    )

    rankings: list["Ranking"] = Relationship(back_populates="team")
