"""Contents endpoint methods for Exa API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kalshi_research.exa.models import (
    ContentsResponse,
    ContextOptions,
    GetContentsRequest,
    HighlightsOptions,
    LivecrawlOption,
    SummaryOptions,
    TextContentsOptions,
)

if TYPE_CHECKING:
    import httpx

    from kalshi_research.exa.config import ExaConfig


class ContentsMixin:
    """Mixin providing contents-related Exa API methods."""

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

    async def get_contents(
        self,
        urls: list[str],
        *,
        text: bool | TextContentsOptions | None = True,
        highlights: bool | HighlightsOptions | None = False,
        summary: bool | SummaryOptions | None = False,
        context: bool | ContextOptions | None = False,
        livecrawl: str | LivecrawlOption = "fallback",
    ) -> ContentsResponse:
        """Fetch document contents for a list of URLs.

        Args:
            urls: URLs to fetch content for.
            text: Whether to include full text in results (or `TextContentsOptions`).
            highlights: Whether to include highlights in results (or `HighlightsOptions`).
            summary: Whether to include summaries in results (or `SummaryOptions`).
            context: Whether to include contextual snippets in results (or `ContextOptions`).
            livecrawl: Exa livecrawl mode (defaults to `"fallback"`).

        Returns:
            Parsed `ContentsResponse`.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaRateLimitError: If rate-limited and retries are exhausted.
            ExaAPIError: For other API/network/response errors.
        """
        request = GetContentsRequest(
            urls=urls,
            text=self._normalize_text_option(text),
            highlights=self._normalize_highlights_option(highlights),
            summary=self._normalize_summary_option(summary),
            context=self._normalize_context_option(context),
            livecrawl=LivecrawlOption(livecrawl) if isinstance(livecrawl, str) else livecrawl,
        )
        data = await self._request(
            "POST",
            "/contents",
            json_body=request.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return ContentsResponse.model_validate(data)
