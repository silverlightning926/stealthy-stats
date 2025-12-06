from sqlmodel import Field, SQLModel


class ETag(SQLModel, table=True):
    __tablename__ = "etags"  # pyright: ignore[reportAssignmentType]

    endpoint: str = Field(
        primary_key=True,
        description="The endpoint the etag is for",
    )

    etag: str = Field(
        description="Cached ETag for the endpoint",
    )
