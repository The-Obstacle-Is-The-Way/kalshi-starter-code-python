"""Models for Exa /findSimilar endpoint."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from kalshi_research.exa.models.common import ContentsRequest, CostDollars
from kalshi_research.exa.models.search import SearchResult


class FindSimilarRequest(BaseModel):
    """Request body for /findSimilar endpoint."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    url: str
    num_results: int = Field(default=10, ge=1, le=100, alias="numResults")
    include_domains: list[str] | None = Field(default=None, alias="includeDomains")
    exclude_domains: list[str] | None = Field(default=None, alias="excludeDomains")
    start_crawl_date: datetime | None = Field(default=None, alias="startCrawlDate")
    end_crawl_date: datetime | None = Field(default=None, alias="endCrawlDate")
    start_published_date: datetime | None = Field(default=None, alias="startPublishedDate")
    end_published_date: datetime | None = Field(default=None, alias="endPublishedDate")
    include_text: list[str] | None = Field(default=None, alias="includeText")
    exclude_text: list[str] | None = Field(default=None, alias="excludeText")
    contents: ContentsRequest | None = None


class FindSimilarResponse(BaseModel):
    """Response from /findSimilar endpoint."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    request_id: str = Field(alias="requestId")
    results: list[SearchResult]
    context: str | None = None
    cost_dollars: CostDollars | None = Field(default=None, alias="costDollars")
    search_time: float | None = Field(default=None, alias="searchTime")
