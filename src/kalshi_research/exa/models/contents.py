"""Models for Exa /contents endpoint."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kalshi_research.exa.models.common import ContentsRequest, CostDollars
from kalshi_research.exa.models.search import SearchResult


class ContentsErrorTag(str, Enum):
    """Error tags returned in ContentsResponse.statuses[].error.tag."""

    CRAWL_NOT_FOUND = "CRAWL_NOT_FOUND"
    CRAWL_TIMEOUT = "CRAWL_TIMEOUT"
    CRAWL_LIVECRAWL_TIMEOUT = "CRAWL_LIVECRAWL_TIMEOUT"
    SOURCE_NOT_AVAILABLE = "SOURCE_NOT_AVAILABLE"
    CRAWL_UNKNOWN_ERROR = "CRAWL_UNKNOWN_ERROR"


class ContentsError(BaseModel):
    """Error details (only when status is 'error')."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    tag: ContentsErrorTag
    http_status_code: int | None = Field(default=None, alias="httpStatusCode")


class ContentsStatus(BaseModel):
    """Per-URL status object in /contents responses."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: str
    status: Literal["success", "error"]
    error: ContentsError | None = None


class GetContentsRequest(ContentsRequest):
    """Request body for /contents endpoint (urls/ids + content options)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    urls: list[str]
    ids: list[str] | None = None


class ContentsResponse(BaseModel):
    """Response from /contents endpoint."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    request_id: str = Field(alias="requestId")
    results: list[SearchResult]
    statuses: list[ContentsStatus]
    context: str | None = None
    cost_dollars: CostDollars | None = Field(default=None, alias="costDollars")
    search_time: float | None = Field(default=None, alias="searchTime")
