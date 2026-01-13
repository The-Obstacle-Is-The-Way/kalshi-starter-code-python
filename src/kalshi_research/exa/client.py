"""Async Exa API client."""

from __future__ import annotations

import asyncio
import json
import math
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Any

import httpx
import structlog

from kalshi_research.exa.config import ExaConfig
from kalshi_research.exa.exceptions import ExaAPIError, ExaAuthError, ExaRateLimitError
from kalshi_research.exa.models import (
    AnswerRequest,
    AnswerResponse,
    ContentsRequest,
    ContentsResponse,
    ContextOptions,
    FindSimilarRequest,
    FindSimilarResponse,
    GetContentsRequest,
    HighlightsOptions,
    ResearchRequest,
    ResearchStatus,
    ResearchTask,
    ResearchTaskListResponse,
    SearchRequest,
    SearchResponse,
    SummaryOptions,
    TextContentsOptions,
)

if TYPE_CHECKING:
    from types import TracebackType

logger = structlog.get_logger()


class ExaClient:
    """
    Async client for Exa API.

    Use as an async context manager:

        async with ExaClient.from_env() as exa:
            results = await exa.search("prediction markets")
    """

    def __init__(self, config: ExaConfig) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None

    @classmethod
    def from_env(cls) -> ExaClient:
        return cls(ExaConfig.from_env())

    async def open(self) -> None:
        if self._client is not None:
            return

        self._client = httpx.AsyncClient(
            base_url=self._config.base_url,
            timeout=self._config.timeout_seconds,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "x-api-key": self._config.api_key,
            },
        )

    async def close(self) -> None:
        if self._client is None:
            return
        await self._client.aclose()
        self._client = None

    async def __aenter__(self) -> ExaClient:
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "ExaClient not initialized. Use 'async with ExaClient(...)' or call open()."
            )
        return self._client

    def _normalize_text_option(
        self, text: bool | TextContentsOptions | None
    ) -> bool | TextContentsOptions | None:
        if isinstance(text, TextContentsOptions):
            return text
        if text:
            return True
        return None

    def _normalize_highlights_option(
        self, highlights: bool | HighlightsOptions | None
    ) -> HighlightsOptions | None:
        if isinstance(highlights, HighlightsOptions):
            return highlights
        if highlights:
            return HighlightsOptions()
        return None

    def _normalize_summary_option(
        self, summary: bool | SummaryOptions | None
    ) -> SummaryOptions | None:
        if isinstance(summary, SummaryOptions):
            return summary
        if summary:
            return SummaryOptions()
        return None

    def _normalize_context_option(
        self, context: bool | ContextOptions | None
    ) -> bool | ContextOptions | None:
        if isinstance(context, ContextOptions):
            return context
        if context:
            return True
        return None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        last_exception: Exception | None = None

        for attempt in range(self._config.max_retries):
            try:
                response = await self.client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json_body,
                )

                if response.status_code == 401:
                    raise ExaAuthError("Invalid API key", status_code=401)

                if response.status_code == 429:
                    retry_after_seconds = self._parse_retry_after(response)
                    if attempt < self._config.max_retries - 1:
                        await asyncio.sleep(float(retry_after_seconds))
                        continue
                    raise ExaRateLimitError(
                        f"Rate limited. Retry after {retry_after_seconds}s",
                        retry_after_seconds=retry_after_seconds,
                    )

                if response.status_code >= 500:
                    if attempt < self._config.max_retries - 1:
                        await asyncio.sleep(self._config.retry_delay_seconds * (attempt + 1))
                        continue
                    raise ExaAPIError(
                        f"API error {response.status_code}: {response.text}",
                        status_code=response.status_code,
                    )

                if response.status_code >= 400:
                    raise ExaAPIError(
                        f"API error {response.status_code}: {response.text}",
                        status_code=response.status_code,
                    )

                try:
                    data: dict[str, Any] = response.json()
                except json.JSONDecodeError as e:
                    raise ExaAPIError(
                        f"Response was not valid JSON: {response.text}",
                        status_code=response.status_code,
                    ) from e

                return data

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                if attempt < self._config.max_retries - 1:
                    await asyncio.sleep(self._config.retry_delay_seconds * (attempt + 1))
                    logger.warning(
                        "Retrying Exa request",
                        path=path,
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    continue
                break

        raise ExaAPIError(
            f"Request failed after {self._config.max_retries} attempts", status_code=None
        ) from last_exception

    def _parse_retry_after(self, response: httpx.Response) -> int:
        retry_after_header = response.headers.get("retry-after")
        if not retry_after_header:
            return int(self._config.retry_delay_seconds)

        retry_after_header = retry_after_header.strip()
        try:
            retry_after_seconds: int = math.ceil(float(retry_after_header))
        except (OverflowError, TypeError, ValueError):
            pass
        else:
            return max(0, retry_after_seconds)

        try:
            retry_at = parsedate_to_datetime(retry_after_header)
        except (OverflowError, TypeError, ValueError):
            return int(self._config.retry_delay_seconds)

        if retry_at.tzinfo is None:
            now = datetime.now()
        else:
            now = datetime.now(UTC).astimezone(retry_at.tzinfo)

        delay = (retry_at - now).total_seconds()
        try:
            delay_seconds: int = math.ceil(delay)
        except OverflowError:
            return int(self._config.retry_delay_seconds)
        return max(0, delay_seconds)

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

    async def get_contents(
        self,
        urls: list[str],
        *,
        text: bool | TextContentsOptions | None = True,
        highlights: bool | HighlightsOptions | None = False,
        summary: bool | SummaryOptions | None = False,
        context: bool | ContextOptions | None = False,
        livecrawl: str = "fallback",
    ) -> ContentsResponse:
        request = GetContentsRequest(
            urls=urls,
            text=self._normalize_text_option(text),
            highlights=self._normalize_highlights_option(highlights),
            summary=self._normalize_summary_option(summary),
            context=self._normalize_context_option(context),
            livecrawl=livecrawl,
        )
        data = await self._request(
            "POST",
            "/contents",
            json_body=request.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return ContentsResponse.model_validate(data)

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

    async def answer(self, query: str, *, text: bool = False) -> AnswerResponse:
        request = AnswerRequest(query=query, text=text)
        data = await self._request(
            "POST",
            "/answer",
            json_body=request.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return AnswerResponse.model_validate(data)

    async def create_research_task(
        self,
        *,
        instructions: str,
        model: str = "exa-research",
        output_schema: dict[str, Any] | None = None,
    ) -> ResearchTask:
        request = ResearchRequest(
            instructions=instructions,
            model=model,
            output_schema=output_schema,
        )
        data = await self._request(
            "POST",
            "/research/v1",
            json_body=request.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return ResearchTask.model_validate(data)

    async def get_research_task(self, research_id: str) -> ResearchTask:
        data = await self._request("GET", f"/research/v1/{research_id}")
        return ResearchTask.model_validate(data)

    async def list_research_tasks(
        self,
        *,
        cursor: str | None = None,
        limit: int = 10,
    ) -> ResearchTaskListResponse:
        if limit < 1 or limit > 50:
            raise ValueError("limit must be between 1 and 50")
        params: dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        data = await self._request("GET", "/research/v1", params=params)
        return ResearchTaskListResponse.model_validate(data)

    async def find_recent_research_task(
        self,
        *,
        instructions_prefix: str | None = None,
        created_after: int | None = None,
        status: ResearchStatus | None = None,
        page_limit: int = 50,
        max_pages: int = 3,
    ) -> ResearchTask | None:
        """
        Find a recent research task matching simple criteria.

        Useful for crash recovery: list tasks, find a likely match, then fetch by ID.
        """
        cursor: str | None = None
        pages_searched = 0

        while True:
            page = await self.list_research_tasks(cursor=cursor, limit=page_limit)
            for item in page.data:
                if instructions_prefix and not item.instructions.startswith(instructions_prefix):
                    continue
                if created_after is not None and item.created_at < created_after:
                    continue
                if status is not None and item.status != status:
                    continue
                return await self.get_research_task(item.research_id)

            pages_searched += 1
            if pages_searched >= max_pages or not page.has_more or page.next_cursor is None:
                return None
            cursor = page.next_cursor

    async def wait_for_research(
        self,
        research_id: str,
        *,
        poll_interval: float = 5.0,
        timeout: float = 300.0,
    ) -> ResearchTask:
        start = time.monotonic()

        while True:
            task = await self.get_research_task(research_id)
            if task.status in (
                ResearchStatus.COMPLETED,
                ResearchStatus.FAILED,
                ResearchStatus.CANCELED,
            ):
                return task

            if time.monotonic() - start >= timeout:
                raise TimeoutError(
                    f"Research task {research_id} did not complete within {timeout}s"
                )

            await asyncio.sleep(poll_interval)
