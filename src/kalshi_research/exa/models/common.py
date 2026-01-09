"""Common types shared across Exa endpoints."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LivecrawlOption(str, Enum):
    """Exa livecrawl behavior."""

    NEVER = "never"
    FALLBACK = "fallback"
    PREFERRED = "preferred"
    ALWAYS = "always"


class TextContentsOptions(BaseModel):
    """Options for extracting full page text."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    max_characters: int | None = Field(default=None, alias="maxCharacters")
    include_html_tags: bool | None = Field(default=None, alias="includeHtmlTags")


class HighlightsOptions(BaseModel):
    """Options for extracting highlight snippets."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    query: str | None = None
    num_sentences: int | None = Field(default=None, alias="numSentences")
    highlights_per_url: int | None = Field(default=None, alias="highlightsPerUrl")


class SummaryOptions(BaseModel):
    """Options for generating an LLM summary (optionally structured)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    query: str | None = None
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")


class ContextOptions(BaseModel):
    """Options for generating combined context strings (RAG)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    max_characters: int | None = Field(default=None, alias="maxCharacters")


class ExtrasOptions(BaseModel):
    """Options for extracting extra metadata (links, images, etc.)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    links: int | None = None
    image_links: int | None = Field(default=None, alias="imageLinks")


class ContentsRequest(BaseModel):
    """Shared contents options used by /search, /findSimilar, and /contents."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    text: bool | TextContentsOptions | None = None
    highlights: bool | HighlightsOptions | None = None
    summary: bool | SummaryOptions | None = None
    context: bool | ContextOptions | None = None
    livecrawl: LivecrawlOption | None = None
    livecrawl_timeout: int | None = Field(default=None, alias="livecrawlTimeout")
    subpages: int | None = None
    subpage_target: str | list[str] | None = Field(default=None, alias="subpageTarget")
    extras: ExtrasOptions | None = None


class CostBreakdownDetails(BaseModel):
    """Fine-grained cost breakdown (when present)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    neural_search: float | None = Field(default=None, alias="neuralSearch")
    deep_search: float | None = Field(default=None, alias="deepSearch")
    content_text: float | None = Field(default=None, alias="contentText")
    content_highlight: float | None = Field(default=None, alias="contentHighlight")
    content_summary: float | None = Field(default=None, alias="contentSummary")


class CostBreakDownItem(BaseModel):
    """High-level cost breakdown entry (when present)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    search: float | None = None
    contents: float | None = None
    breakdown: CostBreakdownDetails | None = None


class PerRequestPrices(BaseModel):
    """Standard prices per request tier (when present)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    neural_search_1_25_results: float | None = Field(
        default=None, alias="neuralSearch_1_25_results"
    )
    neural_search_26_100_results: float | None = Field(
        default=None, alias="neuralSearch_26_100_results"
    )
    neural_search_100_plus_results: float | None = Field(
        default=None, alias="neuralSearch_100_plus_results"
    )
    deep_search_1_25_results: float | None = Field(default=None, alias="deepSearch_1_25_results")
    deep_search_26_100_results: float | None = Field(
        default=None, alias="deepSearch_26_100_results"
    )


class PerPagePrices(BaseModel):
    """Standard prices per page (when present)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    content_text: float | None = Field(default=None, alias="contentText")
    content_highlight: float | None = Field(default=None, alias="contentHighlight")
    content_summary: float | None = Field(default=None, alias="contentSummary")


class CostDollars(BaseModel):
    """Cost information from Exa API."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    total: float
    break_down: list[CostBreakDownItem] | None = Field(default=None, alias="breakDown")
    per_request_prices: PerRequestPrices | None = Field(default=None, alias="perRequestPrices")
    per_page_prices: PerPagePrices | None = Field(default=None, alias="perPagePrices")
