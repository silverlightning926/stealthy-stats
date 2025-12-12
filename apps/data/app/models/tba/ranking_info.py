from sqlmodel import Field, SQLModel


class RankingInfo(SQLModel):
    name: str = Field(
        description="Name of the field used in the extra_stats or sort_orders array."
    )

    precision: int = Field(
        description="Number of digits of precision in the sort_orders values.",
        ge=0,
    )
