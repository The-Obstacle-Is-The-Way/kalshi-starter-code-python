"""Search endpoint methods for Exa API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kalshi_research.exa.models import (
    ContentsRequest,
    ContextOptions,
    FindSimilarRequest,
    FindSimilarResponse,
    HighlightsOptions,
    SearchRequest,
    SearchResponse,
    SummaryOptions,
    TextContentsOptions,
)

if TYPE_CHECKING:
    from datetime import datetime

    import httpx

    from kalshi_research.exa.config import ExaConfig


class SearchMixin:
    """Mixin providing search-related Exa API methods."""

    _config: ExaConfig
    _client: httpx.AsyncClient | None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def _normalize_text_option(
        self, text: bool | TextContentsOptions | None
    ) -> bool | TextContentsOptions | None:
        raise NotImplementedError

    def _normalize_highlights_option(
        self, highlights: bool | HighlightsOptions | None
    ) -> HighlightsOptions | None:
        raise NotImplementedError

    def _normalize_summary_option(
        self, summary: bool | SummaryOptions | None
    ) -> SummaryOptions | None:
        raise NotImplementedError

    def _normalize_context_option(
        self, context: bool | ContextOptions | None
    ) -> bool | ContextOptions | None:
        raise NotImplementedError

    async def search(
        self,
        query: str,
        *,
        search_type: str = "auto",
        additional_queries: list[str] | None = None,
        num_results: int = 10,
        start_published_date: datetime | None = None,
        end_published_date: datetime | None = None,
        start_crawl_date: datetime | None = None,
        end_crawl_date: datetime | None = None,
        user_location: str | None = None,
        moderation: bool | None = None,
        include_text: list[str] | None = None,
        exclude_text: list[str] | None = None,
        text: bool | TextContentsOptions | None = False,
        highlights: bool | HighlightsOptions | None = False,
        summary: bool | SummaryOptions | None = False,
        context: bool | ContextOptions | None = False,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        category: str | None = None,
    ) -> SearchResponse:
        """Search Exa and optionally request document contents.

        Args:
            query: Search query string.
            search_type: Exa search type (defaults to `"auto"`).
            additional_queries: Optional list of additional queries for diversification.
            num_results: Number of results to return.
            start_published_date: Optional lower bound for published date filtering.
            end_published_date: Optional upper bound for published date filtering.
            start_crawl_date: Optional lower bound for crawl date filtering.
            end_crawl_date: Optional upper bound for crawl date filtering.
            user_location: Optional user location for localization.
            moderation: Optional moderation flag.
            include_text: Optional list of required text terms.
            exclude_text: Optional list of excluded text terms.
            text: Whether to include full text in results (or `TextContentsOptions`).
            highlights: Whether to include highlights in results (or `HighlightsOptions`).
            summary: Whether to include summaries in results (or `SummaryOptions`).
            context: Whether to include contextual snippets in results (or `ContextOptions`).
            include_domains: Optional allowlist of domains.
            exclude_domains: Optional blocklist of domains.
            category: Optional Exa category filter.

        Returns:
            Parsed `SearchResponse`.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaRateLimitError: If rate-limited and retries are exhausted.
            ExaAPIError: For other API/network/response errors.
        """
        contents: ContentsRequest | None = None
        text_option = self._normalize_text_option(text)
        highlights_option = self._normalize_highlights_option(highlights)
        summary_option = self._normalize_summary_option(summary)
        context_option = self._normalize_context_option(context)

        if (
            text_option is not None
            or highlights_option is not None
            or summary_option is not None
            or context_option is not None
        ):
            contents = ContentsRequest(
                text=text_option,
                highlights=highlights_option,
                summary=summary_option,
                context=context_option,
            )

        request = SearchRequest(
            query=query,
            search_type=search_type,
            additional_queries=additional_queries,
            num_results=num_results,
            start_published_date=start_published_date,
            end_published_date=end_published_date,
            start_crawl_date=start_crawl_date,
            end_crawl_date=end_crawl_date,
            user_location=user_location,
            moderation=moderation,
            include_text=include_text,
            exclude_text=exclude_text,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            category=category,
            contents=contents,
        )

        data = await self._request(
            "POST",
            "/search",
            json_body=request.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return SearchResponse.model_validate(data)

    async def search_and_contents(
        self,
        query: str,
        *,
        num_results: int = 10,
        search_type: str = "auto",
        additional_queries: list[str] | None = None,
        start_published_date: datetime | None = None,
        end_published_date: datetime | None = None,
        start_crawl_date: datetime | None = None,
        end_crawl_date: datetime | None = None,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        category: str | None = None,
        text: bool | TextContentsOptions | None = True,
        highlights: bool | HighlightsOptions | None = True,
        summary: bool | SummaryOptions | None = False,
        context: bool | ContextOptions | None = False,
    ) -> SearchResponse:
        """Convenience wrapper: search with contents enabled by default."""
        return await self.search(
            query,
            search_type=search_type,
            additional_queries=additional_queries,
            num_results=num_results,
            start_published_date=start_published_date,
            end_published_date=end_published_date,
            start_crawl_date=start_crawl_date,
            end_crawl_date=end_crawl_date,
            text=text,
            highlights=highlights,
            summary=summary,
            context=context,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            category=category,
        )

    async def find_similar(
        self,
        url: str,
        *,
        num_results: int = 10,
        text: bool | TextContentsOptions | None = False,
        highlights: bool | HighlightsOptions | None = False,
        summary: bool | SummaryOptions | None = False,
        context: bool | ContextOptions | None = False,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
    ) -> FindSimilarResponse:
        """Find documents similar to a given URL.

        Args:
            url: URL to find similar documents for.
            num_results: Number of results to return.
            text: Whether to include full text in results (or `TextContentsOptions`).
            highlights: Whether to include highlights in results (or `HighlightsOptions`).
            summary: Whether to include summaries in results (or `SummaryOptions`).
            context: Whether to include contextual snippets in results (or `ContextOptions`).
            include_domains: Optional allowlist of domains.
            exclude_domains: Optional blocklist of domains.

        Returns:
            Parsed `FindSimilarResponse`.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaRateLimitError: If rate-limited and retries are exhausted.
            ExaAPIError: For other API/network/response errors.
        """
        contents: ContentsRequest | None = None
        text_option = self._normalize_text_option(text)
        highlights_option = self._normalize_highlights_option(highlights)
        summary_option = self._normalize_summary_option(summary)
        context_option = self._normalize_context_option(context)

        if (
            text_option is not None
            or highlights_option is not None
            or summary_option is not None
            or context_option is not None
        ):
            contents = ContentsRequest(
                text=text_option,
                highlights=highlights_option,
                summary=summary_option,
                context=context_option,
            )

        request = FindSimilarRequest(
            url=url,
            num_results=num_results,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            contents=contents,
        )
        data = await self._request(
            "POST",
            "/findSimilar",
            json_body=request.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return FindSimilarResponse.model_validate(data)
