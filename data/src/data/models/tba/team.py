from sqlmodel import Field, SQLModel


class Team(SQLModel, table=True):
    key: str = Field(
        primary_key=True,
        description="TBA team key with the format frcXXXX with XXXX representing the team number.",
        regex=r"^frc\d{1,5}$",
    )

    team_number: int = Field(
        index=True,
        description="Official team number issued by FIRST.",
        ge=1,
    )
    nickname: str = Field(description="Team nickname provided by FIRST.")
    name: str = Field(description="Official long name registered with FIRST.")

    school_name: str | None = Field(
        default=None,
        description="Name of team school or affilited group registered with FIRST.",
    )
    city: str | None = Field(
        default=None,
        description="City of team derived from parsing the address registered with FIRST.",
    )
    state_prov: str | None = Field(
        default=None,
        description="State of team derived from parsing the address registered with FIRST.",
    )
    country: str | None = Field(
        default=None,
        description="Country of team derived from parsing the address registered with FIRST.",
    )
    postal_code: str | None = Field(
        default=None, description="Postal code from team address"
    )

    website: str | None = Field(
        default=None, description="Official website associated with the team."
    )
    rookie_year: int | None = Field(
        default=None,
        description="First year the team officially competed.",
        ge=1992,
    )
