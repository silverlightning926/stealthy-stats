from enum import StrEnum
from typing import Any

import httpx
import polars as pl
from pydantic import Field, SecretStr, TypeAdapter
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.models.tba import District, Event, Match, Team


class _TBAEndpoint(StrEnum):
    TEAMS = "/teams/{page}"
    EVENTS = "/events/{year}"
    DISTRICTS = "/districts/{year}"
    MATCHES = "/event/{event_key}/matches"

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


class TBAResponse:
    def __init__(self, data: pl.DataFrame, etag: str | None):
        self.data = data
        self.etag = etag


class TBAService:
    def __init__(self):
        self.config = _TBAConfig()  # pyright: ignore[reportCallIssue]

    def _get(
        self, endpoint: str, etag: str | None = None
    ) -> tuple[list[dict[str, Any]], str | None] | None:
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

    def get_teams(self, page: int, etag: str | None = None) -> TBAResponse | None:
        response = self._get(
            endpoint=_TBAEndpoint.TEAMS.build(page=str(page)),
            etag=etag,
        )

        if response is None:
            return None

        data, etag = response

        TypeAdapter(list[Team]).validate_python(data)

        return TBAResponse(
            data=pl.from_dicts(
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
            etag=etag,
        )

    def get_events(self, year: int, etag: str | None = None) -> TBAResponse | None:
        response = self._get(
            endpoint=_TBAEndpoint.EVENTS.build(year=str(year)),
            etag=etag,
        )

        if response is None:
            return None

        data, etag = response

        events_df = (
            pl.from_dicts(
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
            )
            .filter(  # Filter Out Non In-Season Events
                ~pl.col("event_type").is_in([-1, 7, 99, 100])
            )
            .with_columns(
                pl.col("district").struct.field("key").alias("district_key"),
                pl.col("start_date").str.to_date(),
                pl.col("end_date").str.to_date(),
            )
            .drop("district")
        )

        TypeAdapter(list[Event]).validate_python(events_df.to_dicts())

        return TBAResponse(
            data=events_df,
            etag=etag,
        )

    def get_districts(self, year: int, etag: str | None = None) -> TBAResponse | None:
        response = self._get(
            endpoint=_TBAEndpoint.DISTRICTS.build(year=str(year)),
            etag=etag,
        )

        if response is None:
            return None

        data, etag = response

        TypeAdapter(list[District]).validate_python(data)

        return TBAResponse(
            data=pl.from_dicts(
                data,
                schema={
                    "key": pl.String,
                    "abbreviation": pl.String,
                    "display_name": pl.String,
                    "year": pl.Int32,
                },
            ),
            etag=etag,
        )

    def get_matches(
        self, event_key: str, etag: str | None = None
    ) -> TBAResponse | None:
        response = self._get(
            endpoint=_TBAEndpoint.MATCHES.build(event_key=event_key),
            etag=etag,
        )

        if response is None:
            return None

        data, etag = response

        # TODO: Transform TBA Matches Response To Match DB Schema
        matches_df = pl.from_dicts(data)

        TypeAdapter(list[Match]).validate_python(matches_df.to_dicts())

        return TBAResponse(
            data=matches_df,
            etag=etag,
        )
