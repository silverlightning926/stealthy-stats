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

from app.models.tba import (
    Alliance,
    District,
    Event,
    EventRankingInfo,
    Match,
    MatchAlliance,
    Ranking,
    Team,
)


class _TBAEndpoint(StrEnum):
    TEAMS = "/teams/{page}"
    EVENTS = "/events/{year}"
    DISTRICTS = "/districts/{year}"
    MATCHES = "/event/{event_key}/matches"
    RANKINGS = "/event/{event_key}/rankings"
    ALLIANCES = "/event/{event_key}/alliances"

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
                    "key": pl.String,
                    "team_number": pl.Int32,
                    "nickname": pl.String,
                    "name": pl.String,
                    "school_name": pl.String,
                    "city": pl.String,
                    "state_prov": pl.String,
                    "country": pl.String,
                    "postal_code": pl.String,
                    "website": pl.String,
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
    ) -> tuple[pl.DataFrame, pl.DataFrame, str | None] | None:
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
                    "extra_stats": pl.List(pl.Float64),
                    "sort_orders": pl.List(pl.Float64),
                },
            )
            .unnest("record")
            .with_columns(pl.lit(event_key).alias("event_key"))
            .select("event_key", pl.all().exclude("event_key"))
        )

        ranking_info_df = (
            pl.from_dicts(
                [
                    {
                        "extra_stats_info": data.get("extra_stats_info", []),
                        "sort_order_info": data.get("sort_order_info", []),
                    }
                ],
                schema={
                    "extra_stats_info": pl.List(
                        pl.Struct(
                            {
                                "name": pl.String,
                                "precision": pl.Int32,
                            }
                        )
                    ),
                    "sort_order_info": pl.List(
                        pl.Struct(
                            {
                                "name": pl.String,
                                "precision": pl.Int32,
                            }
                        )
                    ),
                },
            )
            .with_columns(pl.lit(event_key).alias("event_key"))
            .select("event_key", pl.all().exclude("event_key"))
        )

        TypeAdapter(list[Ranking]).validate_python(rankings_df.to_dicts())
        TypeAdapter(list[EventRankingInfo]).validate_python(ranking_info_df.to_dicts())

        return (
            rankings_df,
            ranking_info_df,
            etag,
        )

    def get_alliances(
        self, event_key: str, etag: str | None = None
    ) -> tuple[pl.DataFrame, str | None] | None:
        response = self._get(
            endpoint=_TBAEndpoint.ALLIANCES.build(event_key=event_key),
            etag=etag,
        )

        if response is None:
            return None

        data, etag = response

        alliances_df = (
            pl.from_dicts(
                data,
                schema={
                    "name": pl.String,
                    "picks": pl.List(pl.String),
                    "declines": pl.List(pl.String),
                    "backup": pl.Struct(
                        {
                            "in": pl.String,
                            "out": pl.String,
                        }
                    ),
                    "status": pl.Struct(
                        {
                            "playoff_average": pl.Float64,
                            "playoff_type": pl.Int32,
                            "status": pl.String,
                            "level": pl.String,
                            "record": pl.Struct(
                                {
                                    "wins": pl.Int32,
                                    "losses": pl.Int32,
                                    "ties": pl.Int32,
                                }
                            ),
                            "current_level_record": pl.Struct(
                                {
                                    "wins": pl.Int32,
                                    "losses": pl.Int32,
                                    "ties": pl.Int32,
                                }
                            ),
                            "advanced_to_round_robin_finals": pl.Boolean,
                            "double_elim_round": pl.String,
                            "round_robin_rank": pl.Int32,
                        }
                    ),
                },
            )
            .with_columns(
                pl.col("backup").struct.field("in").alias("backup_in"),
                pl.col("backup").struct.field("out").alias("backup_out"),
            )
            .drop("backup")
            .unnest("status")
            .with_columns(
                pl.col("record").struct.field("wins").alias("wins"),
                pl.col("record").struct.field("losses").alias("losses"),
                pl.col("record").struct.field("ties").alias("ties"),
                pl.col("current_level_record")
                .struct.field("wins")
                .alias("current_level_wins"),
                pl.col("current_level_record")
                .struct.field("losses")
                .alias("current_level_losses"),
                pl.col("current_level_record")
                .struct.field("ties")
                .alias("current_level_ties"),
            )
            .drop(["record", "current_level_record"])
            .with_columns(pl.lit(event_key).alias("event_key"))
            .select("event_key", "name", pl.all().exclude(["event_key", "name"]))
        )

        TypeAdapter(list[Alliance]).validate_python(alliances_df.to_dicts())

        return (alliances_df, etag)
