import logging
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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
    timeout_seconds: int = 30


class TBAService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        self.config = _TBAConfig()  # pyright: ignore[reportCallIssue]
        self.logger.info("TBA Service initialized")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    def _get(self, endpoint: str, etag: str | None = None) -> Any | None:
        self.logger.debug(f"Making request to TBA API: {endpoint}")

        headers = {"X-TBA-Auth-Key": self.config.api_key.get_secret_value()}
        if etag is not None:
            headers["If-None-Match"] = etag
            self.logger.debug(f"Using ETag for request: {etag}")

        try:
            req = httpx.get(
                url=self.config.base_url + endpoint,
                headers=headers,
                timeout=self.config.timeout_seconds,
            )

            if req.status_code == 304:
                self.logger.info(f"Cache hit for endpoint: {endpoint}")
                return None

            req.raise_for_status()
            self.logger.info(f"Successfully fetched data from: {endpoint}")

            return (req.json(), req.headers.get("ETag"))

        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error for endpoint {endpoint}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error for endpoint {endpoint}: {e}")
            raise

    def get_teams(
        self, page: int, etag: str | None = None
    ) -> tuple[pl.DataFrame, str | None] | None:
        self.logger.info(f"Fetching teams page {page}")

        response = self._get(
            endpoint=_TBAEndpoint.TEAMS.build(page=str(page)),
            etag=etag,
        )

        if response is None:
            self.logger.debug(f"Teams page {page} returned 304 (not modified)")
            return None

        data, etag = response

        try:
            TypeAdapter(list[Team]).validate_python(data)

            df = (
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
                )
                .filter(
                    ~pl.col("team_number").is_between(9970, 9999),
                )
                .select("key", pl.all().exclude("key"))
            )

            self.logger.info(f"Processed {len(df)} teams from page {page}")
            return (df, etag)

        except Exception as e:
            self.logger.error(f"Error processing teams data from page {page}: {e}")
            raise

    def get_events(
        self, year: int, etag: str | None = None
    ) -> tuple[pl.DataFrame, pl.DataFrame, str | None] | None:
        self.logger.info(f"Fetching events for year {year}")

        response = self._get(
            endpoint=_TBAEndpoint.EVENTS.build(year=str(year)),
            etag=etag,
        )

        if response is None:
            self.logger.debug(f"Events for year {year} returned 304 (not modified)")
            return None

        data, etag = response

        try:
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
            ).filter(~pl.col("event_type").is_in([-1, 7, 99, 100]))

            districts_df = (
                events_df.select("district")
                .filter(pl.col("district").is_not_null())
                .unnest("district")
                .unique()
                .select("key", pl.all().exclude("key"))
            )

            events_df = (
                events_df.with_columns(
                    pl.col("district").struct.field("key").alias("district_key"),
                    pl.col("start_date").str.to_date(),
                    pl.col("end_date").str.to_date(),
                )
                .drop("district")
                .select("key", pl.all().exclude("key"))
            )

            TypeAdapter(list[Event]).validate_python(events_df.to_dicts())
            TypeAdapter(list[District]).validate_python(districts_df.to_dicts())

            self.logger.info(
                f"Processed {len(events_df)} events and {len(districts_df)} districts for year {year}"
            )

            return (events_df, districts_df, etag)

        except Exception as e:
            self.logger.error(f"Error processing events data for year {year}: {e}")
            raise

    def get_matches(
        self, event_key: str, etag: str | None = None
    ) -> tuple[pl.DataFrame, pl.DataFrame, str | None] | None:
        self.logger.info(f"Fetching matches for event: {event_key}")

        response = self._get(
            endpoint=_TBAEndpoint.MATCHES.build(event_key=str(event_key)),
            etag=etag,
        )

        if response is None:
            self.logger.debug(
                f"Matches for event {event_key} returned 304 (not modified)"
            )
            return None

        data, etag = response

        try:
            matches_df = (
                pl.from_dicts(
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
                )
                .with_columns(
                    [
                        pl.from_epoch("time", time_unit="s"),
                        pl.from_epoch("actual_time", time_unit="s"),
                        pl.from_epoch("predicted_time", time_unit="s"),
                        pl.from_epoch("post_result_time", time_unit="s"),
                    ]
                )
                .select("key", pl.all().exclude("key"))
            )

            match_alliances_df = (
                pl.concat(
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
                .with_columns(
                    [
                        pl.col("team_keys")
                        .list.eval(
                            pl.element().str.extract(r"^frc(\d+)$", 1).cast(pl.Int32)
                        )
                        .list.eval(
                            pl.when(pl.element().is_between(9970, 9999))
                            .then(None)
                            .otherwise(pl.element())
                        )
                        .list.drop_nulls()
                        .list.eval(pl.lit("frc") + pl.element().cast(pl.String))
                        .alias("team_keys"),
                        pl.col("surrogate_team_keys")
                        .list.eval(
                            pl.element().str.extract(r"^frc(\d+)$", 1).cast(pl.Int32)
                        )
                        .list.eval(
                            pl.when(pl.element().is_between(9970, 9999))
                            .then(None)
                            .otherwise(pl.element())
                        )
                        .list.drop_nulls()
                        .list.eval(pl.lit("frc") + pl.element().cast(pl.String))
                        .alias("surrogate_team_keys"),
                        pl.col("dq_team_keys")
                        .list.eval(
                            pl.element().str.extract(r"^frc(\d+)$", 1).cast(pl.Int32)
                        )
                        .list.eval(
                            pl.when(pl.element().is_between(9970, 9999))
                            .then(None)
                            .otherwise(pl.element())
                        )
                        .list.drop_nulls()
                        .list.eval(pl.lit("frc") + pl.element().cast(pl.String))
                        .alias("dq_team_keys"),
                    ]
                )
                .select(
                    "match_key",
                    "alliance_color",
                    pl.all().exclude("match_key", "alliance_color"),
                )
            )

            matches_df = matches_df.drop("alliances", "score_breakdown")

            TypeAdapter(list[Match]).validate_python(matches_df.to_dicts())
            TypeAdapter(list[MatchAlliance]).validate_python(
                match_alliances_df.to_dicts()
            )

            self.logger.info(
                f"Processed {len(matches_df)} matches for event {event_key}"
            )

            return (matches_df, match_alliances_df, etag)

        except Exception as e:
            self.logger.error(
                f"Error processing matches data for event {event_key}: {e}"
            )
            raise

    def get_rankings(
        self, event_key: str, etag: str | None = None
    ) -> tuple[pl.DataFrame, pl.DataFrame, str | None] | None:
        self.logger.info(f"Fetching rankings for event: {event_key}")

        response = self._get(
            endpoint=_TBAEndpoint.RANKINGS.build(event_key=event_key),
            etag=etag,
        )

        if response is None:
            self.logger.debug(
                f"Rankings for event {event_key} returned 304 (not modified)"
            )
            return None

        data, etag = response

        try:
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
                .select(
                    "event_key", "team_key", pl.all().exclude("event_key", "team_key")
                )
                .filter(
                    ~pl.col("team_key")
                    .str.extract(r"^frc(\d+)$", 1)
                    .cast(pl.Int32)
                    .is_between(9970, 9999)
                )
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
            TypeAdapter(list[EventRankingInfo]).validate_python(
                ranking_info_df.to_dicts()
            )

            self.logger.info(
                f"Processed {len(rankings_df)} rankings for event {event_key}"
            )

            return (rankings_df, ranking_info_df, etag)

        except Exception as e:
            self.logger.error(
                f"Error processing rankings data for event {event_key}: {e}"
            )
            raise

    def get_alliances(
        self, event_key: str, etag: str | None = None
    ) -> tuple[pl.DataFrame, str | None] | None:
        self.logger.info(f"Fetching alliances for event: {event_key}")

        response = self._get(
            endpoint=_TBAEndpoint.ALLIANCES.build(event_key=event_key),
            etag=etag,
        )

        if response is None:
            self.logger.debug(
                f"Alliances for event {event_key} returned 304 (not modified)"
            )
            return None

        data, etag = response

        try:
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
                .drop("record", "current_level_record")
                .with_columns(pl.lit(event_key).alias("event_key"))
                .select("event_key", "name", pl.all().exclude("event_key", "name"))
                .with_columns(
                    [
                        pl.col("picks")
                        .list.eval(
                            pl.element().str.extract(r"^frc(\d+)$", 1).cast(pl.Int32)
                        )
                        .list.eval(
                            pl.when(pl.element().is_between(9970, 9999))
                            .then(None)
                            .otherwise(pl.element())
                        )
                        .list.drop_nulls()
                        .list.eval(pl.lit("frc") + pl.element().cast(pl.String))
                        .alias("picks"),
                        pl.col("declines")
                        .list.eval(
                            pl.element().str.extract(r"^frc(\d+)$", 1).cast(pl.Int32)
                        )
                        .list.eval(
                            pl.when(pl.element().is_between(9970, 9999))
                            .then(None)
                            .otherwise(pl.element())
                        )
                        .list.drop_nulls()
                        .list.eval(pl.lit("frc") + pl.element().cast(pl.String))
                        .alias("declines"),
                    ]
                )
                .filter(
                    ~pl.col("backup_in")
                    .str.extract(r"^frc(\d+)$", 1)
                    .cast(pl.Int32)
                    .is_between(9970, 9999, closed="both")
                    | pl.col("backup_in").is_null()
                )
                .filter(
                    ~pl.col("backup_out")
                    .str.extract(r"^frc(\d+)$", 1)
                    .cast(pl.Int32)
                    .is_between(9970, 9999, closed="both")
                    | pl.col("backup_out").is_null()
                )
            )

            TypeAdapter(list[Alliance]).validate_python(alliances_df.to_dicts())

            self.logger.info(
                f"Processed {len(alliances_df)} alliances for event {event_key}"
            )

            return (alliances_df, etag)

        except Exception as e:
            self.logger.error(
                f"Error processing alliances data for event {event_key}: {e}"
            )
            raise
