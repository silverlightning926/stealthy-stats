from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .alliance import Alliance
    from .event import EventTeam


class Team(SQLModel, table=True):
    __tablename__ = "teams"  # pyright: ignore[reportAssignmentType]

    key: str = Field(
        primary_key=True,
        description="TBA team key (e.g., 'frc254').",
        regex=r"^frc\d+$",
    )

    team_number: int = Field(
        index=True,
        gt=0,
        description="Official FIRST team number.",
    )
    nickname: str = Field(
        description="Team nickname.",
    )
    name: str = Field(
        description="Official registered team name.",
    )

    school_name: str | None = Field(
        default=None,
        description="School or organization name.",
    )
    city: str | None = Field(
        default=None,
        description="Team city.",
    )
    state_prov: str | None = Field(
        default=None,
        description="Team state or province.",
    )
    country: str | None = Field(
        default=None,
        description="Team country.",
    )
    postal_code: str | None = Field(
        default=None,
        description="Team postal code.",
    )
    website: str | None = Field(
        default=None,
        description="Team website URL.",
    )
    rookie_year: int | None = Field(
        default=None,
        index=True,
        ge=1992,
        description="Year the team first competed.",
    )

    event_participations: list["EventTeam"] = Relationship(
        back_populates="team",
    )
    alliances_backup_in: list["Alliance"] = Relationship(
        back_populates="team_backup_in",
        sa_relationship_kwargs={
            "primaryjoin": "Team.key == Alliance.backup_in",
            "foreign_keys": "[Alliance.backup_in]",
        },
    )
    alliances_backup_out: list["Alliance"] = Relationship(
        back_populates="team_backup_out",
        sa_relationship_kwargs={
            "primaryjoin": "Team.key == Alliance.backup_out",
            "foreign_keys": "[Alliance.backup_out]",
        },
    )
