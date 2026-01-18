"""Async Exa Websets API client."""

from __future__ import annotations

import asyncio
import json
import math
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Any

import httpx
import structlog

from kalshi_research.exa.config import ExaConfig
from kalshi_research.exa.exceptions import ExaAPIError, ExaAuthError, ExaRateLimitError
from kalshi_research.exa.websets.models import (
    CreateWebsetParameters,
    CreateWebsetSearchParameters,
    GetWebsetResponse,
    ListWebsetItemResponse,
    PreviewWebsetParameters,
    PreviewWebsetResponse,
    Webset,
    WebsetItem,
    WebsetSearch,
)

if TYPE_CHECKING:
    from types import TracebackType

logger = structlog.get_logger()


class ExaWebsetsClient:
    """
    Async client for Exa Websets API.

    Use as an async context manager:

        async with ExaWebsetsClient.from_env() as client:
            webset = await client.create_webset(
                CreateWebsetParameters(
                    search=CreateWebsetSearchParameters(
                        query="AI startups in Europe",
                        count=10
                    )
                )
            )
    """

    def __init__(self, config: ExaConfig) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None

    @classmethod
    def from_env(cls) -> ExaWebsetsClient:
        """Create an `ExaWebsetsClient` using environment configuration.

        Raises:
            ValueError: If required environment variables (e.g., `EXA_API_KEY`) are missing.
        """
        return cls(ExaConfig.from_env())

    async def open(self) -> None:
        """Initialize the underlying `httpx.AsyncClient` if needed."""
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
        """Close the underlying `httpx.AsyncClient` if it is open."""
        if self._client is None:
            return
        await self._client.aclose()
        self._client = None

    async def __aenter__(self) -> ExaWebsetsClient:
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
        """Return the initialized `httpx.AsyncClient`.

        Raises:
            RuntimeError: If `open()` has not been called yet.
        """
        if self._client is None:
            raise RuntimeError(
                "ExaWebsetsClient not initialized. "
                "Use 'async with ExaWebsetsClient(...)' or call open()."
            )
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send an Exa Websets API request with retries and JSON parsing.

        Retries transient failures up to `self._config.max_retries`:
        - `429` responses are retried using the `Retry-After` header when available.
        - `5xx` responses are retried with a linear backoff.
        - Network/timeouts are retried with a linear backoff.

        Args:
            method: HTTP method (e.g., `"GET"`).
            path: Request URL or path for the Exa Websets API.
            params: Optional query parameters.
            json_body: Optional JSON payload for POST-like requests.

        Returns:
            Parsed JSON response payload.

        Raises:
            ExaAuthError: If Exa returns `401` (invalid API key).
            ExaRateLimitError: If Exa returns `429` and retries are exhausted.
            ExaAPIError: For other non-success status codes or invalid JSON responses.
        """
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
                        "Retrying Exa Websets request",
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
        """Return a delay (seconds) derived from a `Retry-After` header.

        Supports numeric values (seconds) or HTTP-date formats. Falls back to the configured
        retry delay when the header is missing or invalid.

        Args:
            response: HTTP response containing potential `Retry-After` headers.

        Returns:
            A non-negative integer delay (in seconds).
        """
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

    async def create_webset(
        self,
        params: CreateWebsetParameters,
    ) -> Webset:
        """Create a new Webset via POST /v0/websets.

        Args:
            params: Parameters for creating the Webset.

        Returns:
            Created `Webset`.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaRateLimitError: If rate-limited and retries are exhausted.
            ExaAPIError: For other API/network/response errors.
        """
        data = await self._request(
            "POST",
            "/v0/websets",
            json_body=params.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return Webset.model_validate(data)

    async def preview_webset(
        self,
        params: PreviewWebsetParameters,
    ) -> PreviewWebsetResponse:
        """Preview a Webset search via POST /v0/websets/preview.

        Args:
            params: Parameters for previewing the Webset.

        Returns:
            Preview response with sample items.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaRateLimitError: If rate-limited and retries are exhausted.
            ExaAPIError: For other API/network/response errors.
        """
        data = await self._request(
            "POST",
            "/v0/websets/preview",
            json_body=params.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return PreviewWebsetResponse.model_validate(data)

    async def get_webset(self, webset_id: str) -> GetWebsetResponse:
        """Get a Webset by ID via GET /v0/websets/{id}.

        Args:
            webset_id: Webset ID.

        Returns:
            Webset details.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaAPIError: If the Webset is not found or other errors occur.
        """
        data = await self._request("GET", f"/v0/websets/{webset_id}")
        return GetWebsetResponse.model_validate(data)

    async def cancel_webset(self, webset_id: str) -> Webset:
        """Cancel a Webset via POST /v0/websets/{id}/cancel.

        Args:
            webset_id: Webset ID.

        Returns:
            Updated Webset with canceled status.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaAPIError: If the Webset is not found or other errors occur.
        """
        data = await self._request("POST", f"/v0/websets/{webset_id}/cancel")
        return Webset.model_validate(data)

    async def list_webset_items(
        self,
        webset_id: str,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> ListWebsetItemResponse:
        """List items in a Webset via GET /v0/websets/{webset}/items.

        Args:
            webset_id: Webset ID.
            cursor: Optional pagination cursor.
            limit: Page size (default 20).

        Returns:
            List of Webset items.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaAPIError: If the Webset is not found or other errors occur.
        """
        params: dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        data = await self._request("GET", f"/v0/websets/{webset_id}/items", params=params)
        return ListWebsetItemResponse.model_validate(data)

    async def get_webset_item(
        self,
        webset_id: str,
        item_id: str,
    ) -> WebsetItem:
        """Get a specific item from a Webset via GET /v0/websets/{webset}/items/{id}.

        Args:
            webset_id: Webset ID.
            item_id: Item ID.

        Returns:
            Webset item details.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaAPIError: If the item is not found or other errors occur.
        """
        data = await self._request("GET", f"/v0/websets/{webset_id}/items/{item_id}")
        return WebsetItem.model_validate(data)

    async def create_webset_search(
        self,
        webset_id: str,
        params: CreateWebsetSearchParameters,
    ) -> WebsetSearch:
        """Create a new search in a Webset via POST /v0/websets/{webset}/searches.

        Args:
            webset_id: Webset ID.
            params: Search parameters.

        Returns:
            Created search.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaAPIError: If the Webset is not found or other errors occur.
        """
        data = await self._request(
            "POST",
            f"/v0/websets/{webset_id}/searches",
            json_body=params.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return WebsetSearch.model_validate(data)

    async def get_webset_search(
        self,
        webset_id: str,
        search_id: str,
    ) -> WebsetSearch:
        """Get a search from a Webset via GET /v0/websets/{webset}/searches/{id}.

        Args:
            webset_id: Webset ID.
            search_id: Search ID.

        Returns:
            Search details.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaAPIError: If the search is not found or other errors occur.
        """
        data = await self._request("GET", f"/v0/websets/{webset_id}/searches/{search_id}")
        return WebsetSearch.model_validate(data)

    async def cancel_webset_search(
        self,
        webset_id: str,
        search_id: str,
    ) -> WebsetSearch:
        """Cancel a search in a Webset via POST /v0/websets/{webset}/searches/{id}/cancel.

        Args:
            webset_id: Webset ID.
            search_id: Search ID.

        Returns:
            Updated search with canceled status.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaAPIError: If the search is not found or other errors occur.
        """
        data = await self._request("POST", f"/v0/websets/{webset_id}/searches/{search_id}/cancel")
        return WebsetSearch.model_validate(data)
