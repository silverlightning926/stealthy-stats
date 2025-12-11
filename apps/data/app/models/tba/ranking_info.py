from sqlmodel import Field, SQLModel


class RankingInfo(SQLModel):
    name: str = Field(
        description="Name of the field used in the extra_stats or sort_orders array."
    )

    precision: int = Field(
        description="Integer expressing the number of digits of precision in the number provided in sort_orders."
    )
