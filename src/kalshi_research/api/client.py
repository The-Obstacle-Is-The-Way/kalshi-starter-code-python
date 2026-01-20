"""Kalshi API clients - public (no auth) and authenticated.

This module provides backward-compatible exports for the Kalshi API clients.
The actual implementation is composed from mixins in the _mixins/ package.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
)

from kalshi_research.api._base import ClientBase, _wait_with_retry_after
from kalshi_research.api._mixins import (
    EventsMixin,
    ExchangeMixin,
    MarketsMixin,
    MultivariateMixin,
    OrderGroupsMixin,
    OrdersMixin,
    PortfolioMixin,
    SeriesMixin,
    TradingMixin,
)
from kalshi_research.api.auth import KalshiAuth
from kalshi_research.api.exceptions import KalshiAPIError, RateLimitError
from kalshi_research.api.rate_limiter import RateTier

logger = structlog.get_logger()


class KalshiPublicClient(
    MarketsMixin,
    EventsMixin,
    MultivariateMixin,
    SeriesMixin,
    ExchangeMixin,
    ClientBase,
):
    """
    Unauthenticated client for public Kalshi API endpoints.

    Use this for market research - no API keys required.
    """

    async def __aenter__(self) -> KalshiPublicClient:
        return self


class KalshiClient(
    PortfolioMixin,
    TradingMixin,
    OrdersMixin,
    OrderGroupsMixin,
    KalshiPublicClient,
):
    """
    Authenticated client extending public client with portfolio endpoints.

    IMPORTANT: Auth signing requires the FULL path including /trade-api/v2 prefix.
    The signature is computed over: timestamp + method + full_path (without query params).
    """

    API_PATH = "/trade-api/v2"

    def __init__(
        self,
        key_id: str,
        private_key_path: str | None = None,
        private_key_b64: str | None = None,
        environment: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 5,
        rate_tier: str | RateTier = RateTier.BASIC,
    ) -> None:
        # Initialize parent (public client infrastructure)
        super().__init__(
            environment=environment,
            timeout=timeout,
            max_retries=max_retries,
            rate_tier=rate_tier,
        )

        # Add authentication
        self._auth = KalshiAuth(
            key_id, private_key_path=private_key_path, private_key_b64=private_key_b64
        )

    async def __aenter__(self) -> KalshiClient:
        return self

    async def _auth_get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Authenticated GET request with retry.

        CRITICAL: Auth signing uses the FULL path including /trade-api/v2 prefix.
        """
        await self._rate_limiter.acquire("GET", path)

        # Sign with full path (e.g., /trade-api/v2/portfolio/balance)
        full_path = self.API_PATH + path
        headers = self._auth.get_headers("GET", full_path)

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(
                (RateLimitError, httpx.NetworkError, httpx.TimeoutException)
            ),
            stop=stop_after_attempt(self._max_retries),
            wait=_wait_with_retry_after,
            reraise=True,
        ):
            with attempt:
                response = await self._client.get(path, params=params, headers=headers)

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
                    raise KalshiAPIError(response.status_code, response.text)

                result: dict[str, Any] = response.json()
                return result

        raise AssertionError("AsyncRetrying should have returned or raised")  # pragma: no cover


# Re-export for backward compatibility
__all__ = ["KalshiClient", "KalshiPublicClient"]
