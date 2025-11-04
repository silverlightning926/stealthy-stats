from typing import Any

import httpx
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from models.tba import Team
from typing import TypeVar, Generic

T = TypeVar("T")


class TBAResponse(Generic[T]):
    def __init__(self, data: T, etag: str | None):
        self.data = data
        self.etag = etag


class _TBAConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: str = Field(..., min_length=1, validation_alias="TBA_API_KEY")
    base_url: str = "https://www.thebluealliance.com/api/v3"
    timeout: int = 10  # In Seconds


class TBAService:
    def __init__(self):
        self.config = _TBAConfig()  # pyright: ignore[reportCallIssue]

    def _get(self, endpoint: str, etag: str | None = None) -> TBAResponse[Any] | None:
        headers = {"X-TBA-Auth-Key": self.config.api_key}
        if etag is not None:
            headers["If-None-Match"] = etag

        req = httpx.get(
            url=self.config.base_url + endpoint,
            headers=headers,
            timeout=self.config.timeout,
        )

        if req.status_code == 304:
            return None

        req.raise_for_status()

        return TBAResponse(data=req.json(), etag=req.headers.get("ETag"))

    def get_teams(
        self, page: int, etag: str | None = None
    ) -> TBAResponse[list[Team]] | None:
        response = self._get(endpoint=f"/teams/{page}", etag=etag)

        if response is None:
            return None

        return TBAResponse(
            data=[Team.model_validate(team_data) for team_data in response.data],
            etag=response.etag,
        )
