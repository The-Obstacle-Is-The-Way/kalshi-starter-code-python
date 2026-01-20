"""Base client infrastructure - HTTP plumbing, retries, rate limiting."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from kalshi_research.api.config import APIConfig, Environment, get_config
from kalshi_research.api.exceptions import KalshiAPIError, RateLimitError
from kalshi_research.api.rate_limiter import RateLimiter, RateTier

if TYPE_CHECKING:
    from tenacity import RetryCallState


logger = structlog.get_logger()

_RETRY_WAIT = wait_exponential(multiplier=1, min=1, max=60)


def _wait_with_retry_after(retry_state: RetryCallState) -> float:
    """Wait using Retry-After header if available, else exponential backoff."""
    outcome = retry_state.outcome
    if outcome is not None:
        exc = outcome.exception()
        if isinstance(exc, RateLimitError) and exc.retry_after is not None:
            return float(exc.retry_after)
    return float(_RETRY_WAIT(retry_state))


class ClientBase:
    """
    Base class for Kalshi API clients.

    Provides HTTP infrastructure, rate limiting, and retry logic.
    """

    _client: httpx.AsyncClient
    _max_retries: int
    _rate_limiter: RateLimiter

    def __init__(
        self,
        environment: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 5,
        rate_tier: str | RateTier = RateTier.BASIC,
    ) -> None:
        config = get_config()
        if environment:
            config = APIConfig(environment=Environment(environment))

        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        self._max_retries = max_retries

        # Initialize rate limiter for read operations
        if isinstance(rate_tier, str):
            rate_tier = RateTier(rate_tier)
        self._rate_limiter = RateLimiter(tier=rate_tier)

    async def __aenter__(self) -> ClientBase:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Make rate-limited GET request with retry.

        Returns:
            JSON response as dictionary.
        """
        # Acquire rate limit for READ
        await self._rate_limiter.acquire("GET", path)

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(
                (
                    RateLimitError,
                    httpx.NetworkError,
                    httpx.TimeoutException,
                )
            ),
            stop=stop_after_attempt(self._max_retries),
            wait=_wait_with_retry_after,
            reraise=True,
        ):
            with attempt:
                response = await self._client.get(path, params=params)

                if response.status_code == 429:
                    retry_after: int | None = None
                    retry_after_header = response.headers.get("Retry-After")
                    if retry_after_header is not None:
                        try:
                            retry_after = int(retry_after_header)
                        except ValueError:
                            retry_after = None
                    raise RateLimitError(
                        message=response.text or "Rate limit exceeded",
                        retry_after=retry_after,
                    )

                if response.status_code >= 400:
                    raise KalshiAPIError(
                        status_code=response.status_code,
                        message=response.text,
                    )
                result: dict[str, Any] = response.json()
                return result

        raise AssertionError("AsyncRetrying should have returned or raised")  # pragma: no cover
