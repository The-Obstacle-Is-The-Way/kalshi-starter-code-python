"""HTTP request plumbing with retry logic for Exa API."""

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

if TYPE_CHECKING:
    from types import TracebackType

logger = structlog.get_logger()


class ExaHTTPBase:
    """
    Base class providing HTTP request infrastructure for Exa API.

    Use as an async context manager:

        async with ExaHTTPBase(config) as client:
            data = await client._request("GET", "/endpoint")
    """

    def __init__(self, config: ExaConfig) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None

    @classmethod
    def from_env(cls) -> ExaHTTPBase:
        """Create an instance using environment configuration.

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

    async def __aenter__(self) -> ExaHTTPBase:
        await self.open()
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    @property
    def client(self) -> httpx.AsyncClient:
        """Return the initialized `httpx.AsyncClient`.

        Raises:
            RuntimeError: If `open()` has not been called yet.
        """
        if self._client is None:
            cls_name = self.__class__.__name__
            raise RuntimeError(
                f"{cls_name} not initialized. "
                f"Use 'async with {cls_name}.from_env()' or call open()."
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
        """Send an Exa API request with retries and JSON parsing.

        Retries transient failures up to `self._config.max_retries`:
        - `429` responses are retried using the `Retry-After` header when available.
        - `5xx` responses are retried with a linear backoff.
        - Network/timeouts are retried with a linear backoff.

        Args:
            method: HTTP method (e.g., `"GET"`).
            path: Request URL or path for the Exa API.
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
