from enum import StrEnum
from typing import Any

import httpx
import polars as pl
from pydantic import Field, SecretStr, TypeAdapter
from pydantic_settings import BaseSettings, SettingsConfigDict
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.models.tba import District, Event, Match, MatchAlliance, Ranking, Team


class _TBAEndpoint(StrEnum):
    TEAMS = "/teams/{page}"
    EVENTS = "/events/{year}"
    DISTRICTS = "/districts/{year}"
    MATCHES = "/event/{event_key}/matches"
    RANKINGS = "/event/{event_key}/rankings"

    def build(self, **kwargs: str) -> str:
        return self.value.format(**kwargs)


class _TBAConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: SecretStr = Field(..., min_length=1, validation_alias="TBA_API_KEY")
    base_url: str = "https://www.thebluealliance.com/api/v3"
    timeout_seconds: int = 30  # In Seconds


class TBAService:
    def __init__(self):
        self.config = _TBAConfig()  # pyright: ignore[reportCallIssue]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    def _get(self, endpoint: str, etag: str | None = None) -> Any | None:
        headers = {"X-TBA-Auth-Key": self.config.api_key.get_secret_value()}
        if etag is not None:
            headers["If-None-Match"] = etag

        req = httpx.get(
            url=self.config.base_url + endpoint,
            headers=headers,
            timeout=self.config.timeout_seconds,
        )

        if req.status_code == 304:
            return None

        req.raise_for_status()

        return (req.json(), req.headers.get("ETag"))

    def get_teams(
        self, page: int, etag: str | None = None
    ) -> tuple[pl.DataFrame, str | None] | None:
        response = self._get(
            endpoint=_TBAEndpoint.TEAMS.build(page=str(page)),
            etag=etag,
        )

        if response is None:
            return None

        data, etag = response

        TypeAdapter(list[Team]).validate_python(data)

        return (
            pl.from_dicts(
                data,
                schema={
                    "key": pl.Utf8,
                    "team_number": pl.Int32,
                    "nickname": pl.Utf8,
                    "name": pl.Utf8,
                    "school_name": pl.Utf8,
                    "city": pl.Utf8,
                    "state_prov": pl.Utf8,
                    "country": pl.Utf8,
                    "postal_code": pl.Utf8,
                    "website": pl.Utf8,
                    "rookie_year": pl.Int32,
                },
            ).filter(  # Filter Out Off-Season Demo Teams
                ~pl.col("nickname").str.contains("(?i)off-?season"),
            ),
            etag,
        )

    def get_events(
        self, year: int, etag: str | None = None
    ) -> tuple[pl.DataFrame, pl.DataFrame, str | None] | None:
        response = self._get(
            endpoint=_TBAEndpoint.EVENTS.build(year=str(year)),
            etag=etag,
        )

        if response is None:
            return None

        data, etag = response

        events_df = pl.from_dicts(
            data,
            schema={
                "key": pl.String,
                "name": pl.String,
                "event_code": pl.String,
                "event_type": pl.Int32,
                "district": pl.Struct(
                    {
                        "key": pl.String,
                        "abbreviation": pl.String,
                        "display_name": pl.String,
                        "year": pl.Int32,
                    }
                ),
                "city": pl.String,
                "state_prov": pl.String,
                "country": pl.String,
                "start_date": pl.String,
                "end_date": pl.String,
                "year": pl.Int32,
                "short_name": pl.String,
                "event_type_string": pl.String,
                "week": pl.Int32,
                "address": pl.String,
                "postal_code": pl.String,
                "gmaps_place_id": pl.String,
                "gmaps_url": pl.String,
                "lat": pl.Float64,
                "lng": pl.Float64,
                "location_name": pl.String,
                "timezone": pl.String,
                "website": pl.String,
                "first_event_id": pl.String,
                "first_event_code": pl.String,
                "division_keys": pl.List(pl.String),
                "parent_event_key": pl.String,
                "playoff_type": pl.Int32,
                "playoff_type_string": pl.String,
            },
        ).filter(  # Filter Out Non In-Season Events
            ~pl.col("event_type").is_in([-1, 7, 99, 100])
        )

        districts_df = (
            events_df.select("district")
            .filter(pl.col("district").is_not_null())
            .unnest("district")
            .unique()
        )

        events_df = events_df.with_columns(
            pl.col("district").struct.field("key").alias("district_key"),
            pl.col("start_date").str.to_date(),
            pl.col("end_date").str.to_date(),
        ).drop("district")

        TypeAdapter(list[Event]).validate_python(events_df.to_dicts())
        TypeAdapter(list[District]).validate_python(districts_df.to_dicts())

        return (
            events_df,
            districts_df,
            etag,
        )

    def get_matches(
        self, event_key: str, etag: str | None = None
    ) -> tuple[pl.DataFrame, pl.DataFrame, str | None] | None:
        response = self._get(
            endpoint=_TBAEndpoint.MATCHES.build(event_key=str(event_key)),
            etag=etag,
        )

        if response is None:
            return None

        data, etag = response

        matches_df = pl.from_dicts(
            data,
            schema={
                "key": pl.String,
                "comp_level": pl.String,
                "set_number": pl.Int32,
                "match_number": pl.Int32,
                "alliances": pl.Struct(
                    {
                        "red": pl.Struct(
                            {
                                "score": pl.Int32,
                                "team_keys": pl.List(pl.String),
                                "surrogate_team_keys": pl.List(pl.String),
                                "dq_team_keys": pl.List(pl.String),
                            }
                        ),
                        "blue": pl.Struct(
                            {
                                "score": pl.Int32,
                                "team_keys": pl.List(pl.String),
                                "surrogate_team_keys": pl.List(pl.String),
                                "dq_team_keys": pl.List(pl.String),
                            }
                        ),
                    }
                ),
                "winning_alliance": pl.String,
                "event_key": pl.String,
                "time": pl.Int64,
                "actual_time": pl.Int64,
                "predicted_time": pl.Int64,
                "post_result_time": pl.Int64,
                "score_breakdown": pl.Object,
            },
        ).with_columns(
            [
                pl.from_epoch("time", time_unit="s"),
                pl.from_epoch("actual_time", time_unit="s"),
                pl.from_epoch("predicted_time", time_unit="s"),
                pl.from_epoch("post_result_time", time_unit="s"),
            ]
        )

        match_alliances_df = pl.concat(
            [
                matches_df.select(
                    [
                        pl.col("key").alias("match_key"),
                        pl.lit("red").alias("alliance_color"),
                        pl.col("alliances")
                        .struct.field("red")
                        .struct.field("score")
                        .alias("score"),
                        pl.col("alliances")
                        .struct.field("red")
                        .struct.field("team_keys")
                        .alias("team_keys"),
                        pl.col("alliances")
                        .struct.field("red")
                        .struct.field("surrogate_team_keys")
                        .alias("surrogate_team_keys"),
                        pl.col("alliances")
                        .struct.field("red")
                        .struct.field("dq_team_keys")
                        .alias("dq_team_keys"),
                        pl.col("score_breakdown")
                        .map_elements(
                            lambda x: x.get("red") if x else None,
                            return_dtype=pl.Object,
                        )
                        .alias("score_breakdown"),
                    ]
                ),
                matches_df.select(
                    [
                        pl.col("key").alias("match_key"),
                        pl.lit("blue").alias("alliance_color"),
                        pl.col("alliances")
                        .struct.field("blue")
                        .struct.field("score")
                        .alias("score"),
                        pl.col("alliances")
                        .struct.field("blue")
                        .struct.field("team_keys")
                        .alias("team_keys"),
                        pl.col("alliances")
                        .struct.field("blue")
                        .struct.field("surrogate_team_keys")
                        .alias("surrogate_team_keys"),
                        pl.col("alliances")
                        .struct.field("blue")
                        .struct.field("dq_team_keys")
                        .alias("dq_team_keys"),
                        pl.col("score_breakdown")
                        .map_elements(
                            lambda x: x.get("blue") if x else None,
                            return_dtype=pl.Object,
                        )
                        .alias("score_breakdown"),
                    ]
                ),
            ]
        )

        matches_df = matches_df.drop(["alliances", "score_breakdown"])

        TypeAdapter(list[Match]).validate_python(matches_df.to_dicts())
        TypeAdapter(list[MatchAlliance]).validate_python(match_alliances_df.to_dicts())

        return (
            matches_df,
            match_alliances_df,
            etag,
        )

    def get_rankings(
        self, event_key: str, etag: str | None = None
    ) -> tuple[pl.DataFrame, str | None] | None:
        response = self._get(
            endpoint=_TBAEndpoint.RANKINGS.build(event_key=event_key),
            etag=etag,
        )

        if response is None:
            return None

        data, etag = response

        rankings_df = (
            pl.from_dicts(
                data.get("rankings", []),
                schema={
                    "team_key": pl.String,
                    "rank": pl.Int32,
                    "matches_played": pl.Int32,
                    "qual_average": pl.Int32,
                    "dq": pl.Int32,
                    "record": pl.Struct(
                        {
                            "wins": pl.Int32,
                            "losses": pl.Int32,
                            "ties": pl.Int32,
                        }
                    ),
                },
            )
            .unnest("record")
            .with_columns(pl.lit(event_key).alias("event_key"))
            .select("event_key", pl.all().exclude("event_key"))
        )

        TypeAdapter(list[Ranking]).validate_python(rankings_df.to_dicts())

        return (
            rankings_df,
            etag,
        )
