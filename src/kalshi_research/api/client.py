"""Kalshi API clients - public (no auth) and authenticated."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from kalshi_research.api.auth import KalshiAuth
from kalshi_research.api.exceptions import KalshiAPIError, RateLimitError
from kalshi_research.api.models.candlestick import Candlestick, CandlestickResponse
from kalshi_research.api.models.event import Event
from kalshi_research.api.models.market import Market, MarketFilterStatus
from kalshi_research.api.models.orderbook import Orderbook
from kalshi_research.api.models.trade import Trade

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class KalshiPublicClient:
    """
    Unauthenticated client for public Kalshi API endpoints.

    Use this for market research - no API keys required.
    """

    BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 5,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        self._max_retries = max_retries

    async def __aenter__(self) -> KalshiPublicClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self._client.aclose()

    @retry(
        retry=retry_if_exception_type((RateLimitError, httpx.NetworkError, httpx.TimeoutException)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=60),
    )
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make rate-limited GET request with retry."""
        response = await self._client.get(path, params=params)

        if response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")

        if response.status_code >= 400:
            raise KalshiAPIError(
                status_code=response.status_code,
                message=response.text,
            )
        result: dict[str, Any] = response.json()
        return result

    # ==================== Markets ====================

    async def get_markets(
        self,
        status: MarketFilterStatus | str | None = None,
        event_ticker: str | None = None,
        series_ticker: str | None = None,
        limit: int = 100,
    ) -> list[Market]:
        """
        Fetch markets with optional filters.

        Note: status filter uses different values than response status field.
        Filter: unopened, open, closed, settled
        Response: active, closed, determined, finalized
        """
        params: dict[str, Any] = {"limit": min(limit, 1000)}
        if status:
            params["status"] = status.value if isinstance(status, MarketFilterStatus) else status
        if event_ticker:
            params["event_ticker"] = event_ticker
        if series_ticker:
            params["series_ticker"] = series_ticker

        data = await self._get("/markets", params)
        return [Market.model_validate(m) for m in data.get("markets", [])]

    async def get_all_markets(
        self,
        status: MarketFilterStatus | str | None = None,
        max_pages: int = 100,
    ) -> AsyncIterator[Market]:
        """
        Iterate through ALL markets with automatic pagination.
        Includes a safety limit to prevent infinite loops.
        """
        cursor: str | None = None
        pages = 0
        while pages < max_pages:
            params: dict[str, Any] = {"limit": 1000}
            if status:
                params["status"] = (
                    status.value if isinstance(status, MarketFilterStatus) else status
                )
            if cursor:
                params["cursor"] = cursor

            data = await self._get("/markets", params)
            markets = data.get("markets", [])

            for market_data in markets:
                yield Market.model_validate(market_data)

            cursor = data.get("cursor")
            if not cursor or not markets:
                break
            pages += 1

    async def get_market(self, ticker: str) -> Market:
        """Fetch single market by ticker."""
        data = await self._get(f"/markets/{ticker}")
        return Market.model_validate(data["market"])

    async def get_orderbook(self, ticker: str, depth: int = 10) -> Orderbook:
        """
        Fetch current orderbook for a market.

        Note: Orderbook returns yes/no bids only (no asks).
        Each is a list of [price, quantity] tuples, or null if empty.
        """
        data = await self._get(f"/markets/{ticker}/orderbook", params={"depth": depth})
        return Orderbook.model_validate(data["orderbook"])

    async def get_trades(
        self,
        ticker: str | None = None,
        limit: int = 100,
        min_ts: int | None = None,
        max_ts: int | None = None,
    ) -> list[Trade]:
        """Fetch public trade history."""
        params: dict[str, Any] = {"limit": min(limit, 1000)}
        if ticker:
            params["ticker"] = ticker
        if min_ts:
            params["min_ts"] = min_ts
        if max_ts:
            params["max_ts"] = max_ts

        data = await self._get("/markets/trades", params)
        return [Trade.model_validate(t) for t in data.get("trades", [])]

    async def get_candlesticks(
        self,
        market_tickers: list[str],
        start_ts: int,
        end_ts: int,
        period_interval: int = 60,
    ) -> list[CandlestickResponse]:
        """
        Fetch OHLC candlestick data for multiple markets (batch endpoint).

        Args:
            market_tickers: List of market tickers (max 100)
            start_ts: Start timestamp (Unix seconds)
            end_ts: End timestamp (Unix seconds)
            period_interval: Candle period in minutes (1, 60, or 1440)

        Returns:
            List of CandlestickResponse, one per market
        """
        if len(market_tickers) > 100:
            raise ValueError("Maximum 100 market tickers per request")

        params: dict[str, Any] = {
            "market_tickers": ",".join(market_tickers),
            "start_ts": start_ts,
            "end_ts": end_ts,
            "period_interval": period_interval,
        }

        data = await self._get("/markets/candlesticks", params)
        return [CandlestickResponse.model_validate(m) for m in data.get("markets", [])]

    async def get_series_candlesticks(
        self,
        series_ticker: str,
        ticker: str,
        start_ts: int | None = None,
        end_ts: int | None = None,
        period_interval: int = 60,
    ) -> list[Candlestick]:
        """
        Fetch OHLC candlestick data for a single market within a series.

        Args:
            series_ticker: The series ticker
            ticker: The market ticker
            start_ts: Optional start timestamp (Unix seconds)
            end_ts: Optional end timestamp (Unix seconds)
            period_interval: Candle period in minutes (1, 60, or 1440)
        """
        params: dict[str, Any] = {"period_interval": period_interval}
        if start_ts:
            params["start_ts"] = start_ts
        if end_ts:
            params["end_ts"] = end_ts

        data = await self._get(f"/series/{series_ticker}/markets/{ticker}/candlesticks", params)
        return [Candlestick.model_validate(c) for c in data.get("candlesticks", [])]

    # ==================== Events ====================

    async def get_events(
        self,
        status: MarketFilterStatus | str | None = None,
        series_ticker: str | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Fetch events with optional filters."""
        # Events endpoint max limit is 200 (not 1000 like markets)
        params: dict[str, Any] = {"limit": min(limit, 200)}
        if status:
            params["status"] = status.value if isinstance(status, MarketFilterStatus) else status
        if series_ticker:
            params["series_ticker"] = series_ticker

        data = await self._get("/events", params)
        return [Event.model_validate(e) for e in data.get("events", [])]

    async def get_event(self, event_ticker: str) -> Event:
        """Fetch single event by ticker."""
        data = await self._get(f"/events/{event_ticker}")
        return Event.model_validate(data["event"])

    # ==================== Exchange ====================

    async def get_exchange_status(self) -> dict[str, Any]:
        """Check if exchange is operational."""
        return await self._get("/exchange/status")


class KalshiClient(KalshiPublicClient):
    """
    Authenticated client extending public client with portfolio endpoints.

    IMPORTANT: Auth signing requires the FULL path including /trade-api/v2 prefix.
    The signature is computed over: timestamp + method + full_path (without query params).
    """

    DEMO_BASE = "https://demo-api.kalshi.co"
    PROD_BASE = "https://api.elections.kalshi.com"
    API_PATH = "/trade-api/v2"

    def __init__(
        self,
        key_id: str,
        private_key_path: str,
        environment: str = "prod",
        timeout: float = 30.0,
    ) -> None:
        # Don't call super().__init__() - we create client with environment-specific URL
        base_host = self.DEMO_BASE if environment == "demo" else self.PROD_BASE
        self._base_url = base_host + self.API_PATH
        self._auth = KalshiAuth(key_id, private_key_path)
        self._max_retries = 5

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    async def __aenter__(self) -> KalshiClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self._client.aclose()

    @retry(
        retry=retry_if_exception_type((RateLimitError, httpx.NetworkError, httpx.TimeoutException)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=60),
    )
    async def _auth_get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Authenticated GET request with retry.

        CRITICAL: Auth signing uses the FULL path including /trade-api/v2 prefix.
        """
        # Sign with full path (e.g., /trade-api/v2/portfolio/balance)
        full_path = self.API_PATH + path
        headers = self._auth.get_headers("GET", full_path)
        response = await self._client.get(path, params=params, headers=headers)

        if response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")

        if response.status_code >= 400:
            raise KalshiAPIError(response.status_code, response.text)

        result: dict[str, Any] = response.json()
        return result

    async def get_balance(self) -> dict[str, Any]:
        """Get account balance."""
        return await self._auth_get("/portfolio/balance")

    async def get_positions(self) -> list[dict[str, Any]]:
        """Get current positions."""
        data = await self._auth_get("/portfolio/positions")
        positions: list[dict[str, Any]] = data.get("positions", [])
        return positions

    async def get_orders(
        self,
        ticker: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get order history."""
        params: dict[str, Any] = {}
        if ticker:
            params["ticker"] = ticker
        if status:
            params["status"] = status
        data = await self._auth_get("/portfolio/orders", params or None)
        orders: list[dict[str, Any]] = data.get("orders", [])
        return orders
