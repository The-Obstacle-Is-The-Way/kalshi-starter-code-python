"""Models for Exa /search endpoint."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from kalshi_research.exa.models.common import ContentsRequest, CostDollars


class SearchType(str, Enum):
    """Exa search type."""

    NEURAL = "neural"
    FAST = "fast"
    AUTO = "auto"
    DEEP = "deep"


class SearchCategory(str, Enum):
    """Exa search category filter."""

    RESEARCH_PAPER = "research paper"
    NEWS = "news"
    PDF = "pdf"
    GITHUB = "github"
    TWEET = "tweet"
    PERSONAL_SITE = "personal site"
    FINANCIAL_REPORT = "financial report"
    COMPANY = "company"
    PEOPLE = "people"


class SearchRequest(BaseModel):
    """Request body for /search endpoint."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    query: str
    search_type: SearchType = Field(default=SearchType.AUTO, alias="type")
    additional_queries: list[str] | None = Field(default=None, alias="additionalQueries")
    num_results: int = Field(default=10, ge=1, le=100, alias="numResults")
    include_domains: list[str] | None = Field(default=None, alias="includeDomains")
    exclude_domains: list[str] | None = Field(default=None, alias="excludeDomains")
    start_crawl_date: datetime | None = Field(default=None, alias="startCrawlDate")
    end_crawl_date: datetime | None = Field(default=None, alias="endCrawlDate")
    start_published_date: datetime | None = Field(default=None, alias="startPublishedDate")
    end_published_date: datetime | None = Field(default=None, alias="endPublishedDate")
    user_location: str | None = Field(default=None, alias="userLocation")
    moderation: bool | None = None
    include_text: list[str] | None = Field(default=None, alias="includeText")
    exclude_text: list[str] | None = Field(default=None, alias="excludeText")
    category: SearchCategory | None = None
    contents: ContentsRequest | None = None


class SearchResult(BaseModel):
    """Individual search result."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: str
    url: str
    title: str
    published_date: datetime | None = Field(default=None, alias="publishedDate")
    author: str | None = None
    score: float | None = None
    image: str | None = None
    favicon: str | None = None

    # Content fields (present if requested)
    text: str | None = None
    summary: str | None = None
    highlights: list[str] | None = None
    highlight_scores: list[float] | None = Field(default=None, alias="highlightScores")
    subpages: list[SearchResult] | None = None
    extras: dict[str, Any] | None = None

    @field_validator("published_date", mode="before")
    @classmethod
    def coerce_empty_published_date(cls, value: object) -> object:
        """Convert empty-string `publishedDate` values to `None`."""
        if isinstance(value, str) and not value.strip():
            return None
        return value


class SearchResponse(BaseModel):
    """Response from /search endpoint."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    request_id: str = Field(alias="requestId")
    results: list[SearchResult]
    search_type: str | None = Field(
        default=None,
        alias="searchType",
        validation_alias=AliasChoices("searchType", "resolvedSearchType"),
    )
    auto_date: str | None = Field(default=None, alias="autoDate")
    context: str | None = None
    cost_dollars: CostDollars | None = Field(default=None, alias="costDollars")
    search_time: float | None = Field(default=None, alias="searchTime")
