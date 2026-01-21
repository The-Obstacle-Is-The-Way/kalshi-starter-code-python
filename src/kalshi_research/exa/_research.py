"""Research task endpoint methods for Exa API."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from kalshi_research.exa.models import (
    ResearchRequest,
    ResearchStatus,
    ResearchTask,
    ResearchTaskListResponse,
)

if TYPE_CHECKING:
    import httpx

    from kalshi_research.exa.config import ExaConfig


class ResearchMixin:
    """Mixin providing research task-related Exa API methods."""

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

    async def create_research_task(
        self,
        *,
        instructions: str,
        model: str = "exa-research",
        output_schema: dict[str, Any] | None = None,
    ) -> ResearchTask:
        """Create a deep research task via Exa `/research/v1`.

        Args:
            instructions: Research instructions prompt.
            model: Exa research model tier (e.g., `"exa-research-fast"`, `"exa-research"`).
            output_schema: Optional JSON schema to constrain structured output.

        Returns:
            Created `ResearchTask` (includes a `research_id` for polling).

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaRateLimitError: If rate-limited and retries are exhausted.
            ExaAPIError: For other API/network/response errors.
        """
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
        """Fetch a research task by ID via Exa `/research/v1/{research_id}`."""
        data = await self._request("GET", f"/research/v1/{research_id}")
        return ResearchTask.model_validate(data)

    async def list_research_tasks(
        self,
        *,
        cursor: str | None = None,
        limit: int = 10,
    ) -> ResearchTaskListResponse:
        """List research tasks via Exa `/research/v1`.

        Args:
            cursor: Optional pagination cursor for the next page.
            limit: Page size (1-50).

        Returns:
            Parsed `ResearchTaskListResponse`.

        Raises:
            ValueError: If `limit` is outside the allowed range.
            ExaAuthError: If the API key is invalid.
            ExaRateLimitError: If rate-limited and retries are exhausted.
            ExaAPIError: For other API/network/response errors.
        """
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
        """Poll a research task until it reaches a terminal status.

        Args:
            research_id: Exa research task ID.
            poll_interval: Seconds to wait between polls.
            timeout: Max time to wait before raising `TimeoutError`.

        Returns:
            Final `ResearchTask` (terminal status: completed/failed/canceled).

        Raises:
            TimeoutError: If the task does not complete within `timeout` seconds.
            ExaAuthError: If the API key is invalid.
            ExaRateLimitError: If rate-limited and retries are exhausted.
            ExaAPIError: For other API/network/response errors.
        """
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
