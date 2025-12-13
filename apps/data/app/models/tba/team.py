from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .alliance import Alliance, AllianceTeam
    from .match import MatchAllianceTeam
    from .ranking import Ranking


class Team(SQLModel, table=True):
    __tablename__ = "teams"  # type: ignore[reportAssignmentType]

    key: str = Field(
        primary_key=True,
        description="TBA team key with format 'frcXXXX' where XXXX is the team number.",
        regex=r"^frc\d+$",
    )

    team_number: int = Field(
        index=True,
        description="Official team number issued by FIRST.",
        gt=0,
    )

    nickname: str = Field(
        description="Team nickname provided by FIRST.",
    )

    name: str = Field(
        description="Official long name registered with FIRST.",
    )

    school_name: str | None = Field(
        default=None,
        description="Name of team school or affiliated group registered with FIRST.",
    )

    city: str | None = Field(
        default=None,
        description="City derived from the address registered with FIRST.",
    )

    state_prov: str | None = Field(
        default=None,
        description="State/province derived from the address registered with FIRST.",
    )

    country: str | None = Field(
        default=None,
        description="Country derived from the address registered with FIRST.",
    )

    postal_code: str | None = Field(
        default=None,
        description="Postal code from the team address.",
    )

    website: str | None = Field(
        default=None,
        description="Official website associated with the team.",
    )

    rookie_year: int | None = Field(
        default=None,
        description="First year the team officially competed.",
        ge=1992,
    )

    rankings: list["Ranking"] = Relationship(back_populates="team")

    alliance_participations: list["AllianceTeam"] = Relationship(back_populates="team")

    alliances_backup_in: list["Alliance"] = Relationship(
        back_populates="team_backup_in",
        sa_relationship_kwargs={
            "foreign_keys": "[Alliance.backup_in]",
            "primaryjoin": "Team.key == Alliance.backup_in",
        },
    )

    alliances_backup_out: list["Alliance"] = Relationship(
        back_populates="team_backup_out",
        sa_relationship_kwargs={
            "foreign_keys": "[Alliance.backup_out]",
            "primaryjoin": "Team.key == Alliance.backup_out",
        },
    )

    match_participations: list["MatchAllianceTeam"] = Relationship(
        back_populates="team"
    )
