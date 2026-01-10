"""Kalshi API clients - public (no auth) and authenticated."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Literal

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from kalshi_research.api.auth import KalshiAuth
from kalshi_research.api.config import APIConfig, Environment, get_config
from kalshi_research.api.exceptions import KalshiAPIError, RateLimitError
from kalshi_research.api.models.candlestick import Candlestick, CandlestickResponse
from kalshi_research.api.models.event import Event
from kalshi_research.api.models.market import Market, MarketFilterStatus
from kalshi_research.api.models.order import OrderAction, OrderResponse, OrderSide
from kalshi_research.api.models.orderbook import Orderbook
from kalshi_research.api.models.portfolio import (
    CancelOrderResponse,
    FillPage,
    OrderPage,
    PortfolioBalance,
    PortfolioPosition,
)
from kalshi_research.api.models.trade import Trade
from kalshi_research.api.rate_limiter import RateLimiter, RateTier

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from tenacity import RetryCallState


logger = structlog.get_logger()

_RETRY_WAIT = wait_exponential(multiplier=1, min=1, max=60)


def _wait_with_retry_after(retry_state: RetryCallState) -> float:
    outcome = retry_state.outcome
    if outcome is not None:
        exc = outcome.exception()
        if isinstance(exc, RateLimitError) and exc.retry_after is not None:
            return float(exc.retry_after)
    return float(_RETRY_WAIT(retry_state))


class KalshiPublicClient:
    """
    Unauthenticated client for public Kalshi API endpoints.

    Use this for market research - no API keys required.
    """

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

    async def __aenter__(self) -> KalshiPublicClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
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

    # ==================== Markets ====================

    async def get_markets_page(
        self,
        status: MarketFilterStatus | str | None = None,
        event_ticker: str | None = None,
        series_ticker: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
        mve_filter: Literal["only", "exclude"] | None = None,
    ) -> tuple[list[Market], str | None]:
        """
        Fetch a single page of markets and return the next cursor (if any).

        Note: status filter uses different values than response status field.
        Filter: unopened, open, closed, settled
        Response: active, closed, determined, finalized
        """
        # 1000 is Kalshi API max limit per page (see docs/_vendor-docs/kalshi-api-reference.md)
        params: dict[str, Any] = {"limit": min(limit, 1000)}
        if status:
            params["status"] = status.value if isinstance(status, MarketFilterStatus) else status
        if event_ticker:
            params["event_ticker"] = event_ticker
        if series_ticker:
            params["series_ticker"] = series_ticker
        if cursor:
            params["cursor"] = cursor
        if mve_filter:
            params["mve_filter"] = mve_filter

        data = await self._get("/markets", params)
        markets = [Market.model_validate(m) for m in data.get("markets", [])]
        return markets, data.get("cursor")

    async def get_markets(
        self,
        status: MarketFilterStatus | str | None = None,
        event_ticker: str | None = None,
        series_ticker: str | None = None,
        limit: int = 100,
        mve_filter: Literal["only", "exclude"] | None = None,
    ) -> list[Market]:
        """
        Fetch markets with optional filters.

        Note: status filter uses different values than response status field.
        Filter: unopened, open, closed, settled
        Response: active, closed, determined, finalized
        """
        markets, _ = await self.get_markets_page(
            status=status,
            event_ticker=event_ticker,
            series_ticker=series_ticker,
            limit=limit,
            mve_filter=mve_filter,
        )
        return markets

    async def get_all_markets(
        self,
        status: MarketFilterStatus | str | None = None,
        limit: int = 1000,
        max_pages: int | None = None,
        mve_filter: Literal["only", "exclude"] | None = None,
    ) -> AsyncIterator[Market]:
        """
        Iterate through ALL markets with automatic pagination.

        Args:
            status: Filter by market status (open, closed, settled)
            limit: Page size (max 1000)
            max_pages: Optional safety limit. None = iterate until exhausted.
            mve_filter: Filter for multivariate events ("only" or "exclude")

        Yields:
            Market objects

        Warns:
            If max_pages reached but cursor still present (data truncated)
        """
        cursor: str | None = None
        pages = 0
        while True:
            markets, cursor = await self.get_markets_page(
                status=status,
                limit=limit,
                cursor=cursor,
                mve_filter=mve_filter,
            )

            for market in markets:
                yield market

            if not cursor or not markets:
                break

            pages += 1

            # Safety limit check with warning
            if max_pages is not None and pages >= max_pages:
                logger.warning(
                    "Pagination truncated: reached max_pages but cursor still present. "
                    "Data may be incomplete. Set max_pages=None for full iteration.",
                    max_pages=max_pages,
                )
                break

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
        # 1000 is Kalshi API max limit per page (see docs/_vendor-docs/kalshi-api-reference.md)
        params: dict[str, Any] = {"limit": min(limit, 1000)}
        if ticker:
            params["ticker"] = ticker
        if min_ts is not None:
            params["min_ts"] = min_ts
        if max_ts is not None:
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
        if start_ts is not None:
            params["start_ts"] = start_ts
        if end_ts is not None:
            params["end_ts"] = end_ts

        data = await self._get(f"/series/{series_ticker}/markets/{ticker}/candlesticks", params)
        return [Candlestick.model_validate(c) for c in data.get("candlesticks", [])]

    # ==================== Events ====================

    async def get_events_page(
        self,
        status: MarketFilterStatus | str | None = None,
        series_ticker: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> tuple[list[Event], str | None]:
        """Fetch a single page of events and return the next cursor (if any)."""
        # Events endpoint max limit is 200 (not 1000 like markets)
        params: dict[str, Any] = {"limit": min(limit, 200)}
        if status:
            params["status"] = status.value if isinstance(status, MarketFilterStatus) else status
        if series_ticker:
            params["series_ticker"] = series_ticker
        if cursor:
            params["cursor"] = cursor

        data = await self._get("/events", params)
        events = [Event.model_validate(e) for e in data.get("events", [])]
        return events, data.get("cursor")

    async def get_events(
        self,
        status: MarketFilterStatus | str | None = None,
        series_ticker: str | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Fetch events with optional filters."""
        events, _ = await self.get_events_page(
            status=status,
            series_ticker=series_ticker,
            limit=limit,
        )
        return events

    async def get_all_events(
        self,
        status: MarketFilterStatus | str | None = None,
        series_ticker: str | None = None,
        limit: int = 200,
        max_pages: int | None = None,
    ) -> AsyncIterator[Event]:
        """
        Iterate through ALL events with automatic pagination.

        Args:
            status: Filter by event status
            series_ticker: Filter by series
            limit: Page size (max 200 for events endpoint)
            max_pages: Optional safety limit. None = iterate until exhausted.

        Yields:
            Event objects

        Warns:
            If max_pages reached but cursor still present (data truncated)
        """
        cursor: str | None = None
        pages = 0
        while True:
            events, cursor = await self.get_events_page(
                status=status,
                series_ticker=series_ticker,
                limit=limit,
                cursor=cursor,
            )

            for event in events:
                yield event

            if not cursor or not events:
                break

            pages += 1

            # Safety limit check with warning
            if max_pages is not None and pages >= max_pages:
                logger.warning(
                    "Pagination truncated: reached max_pages but cursor still present. "
                    "Data may be incomplete. Set max_pages=None for full iteration.",
                    max_pages=max_pages,
                )
                break

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
        # Resolve configuration
        config = get_config()
        if environment:
            config = APIConfig(environment=Environment(environment))

        self._base_url = config.base_url
        self._auth = KalshiAuth(
            key_id, private_key_path=private_key_path, private_key_b64=private_key_b64
        )
        self._max_retries = max_retries

        # Initialize rate limiter
        if isinstance(rate_tier, str):
            rate_tier = RateTier(rate_tier)
        self._rate_limiter = RateLimiter(tier=rate_tier)

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

    async def _auth_get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Authenticated GET request with retry.

        CRITICAL: Auth signing uses the FULL path including /trade-api/v2 prefix.
        """
        # Acquire rate limit for READ
        await self._rate_limiter.acquire("GET", path)

        # Sign with full path (e.g., /trade-api/v2/portfolio/balance)
        full_path = self.API_PATH + path
        headers = self._auth.get_headers("GET", full_path)
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

    async def get_balance(self) -> PortfolioBalance:
        """Get account balance."""
        data = await self._auth_get("/portfolio/balance")
        return PortfolioBalance.model_validate(data)

    async def get_positions(self) -> list[PortfolioPosition]:
        """Get current market positions."""
        data = await self._auth_get("/portfolio/positions")
        # NOTE: Kalshi returns `market_positions` (and `event_positions`). Older docs/examples may
        # reference `positions`, so keep a fallback for compatibility.
        raw = data.get("market_positions") or data.get("positions") or []
        if not isinstance(raw, list):
            return []
        return [PortfolioPosition.model_validate(pos) for pos in raw]

    async def get_orders(
        self,
        ticker: str | None = None,
        status: str | None = None,
    ) -> OrderPage:
        """Get order history."""
        params: dict[str, Any] = {}
        if ticker:
            params["ticker"] = ticker
        if status:
            params["status"] = status
        data = await self._auth_get("/portfolio/orders", params or None)
        return OrderPage.model_validate(data)

    async def get_fills(
        self,
        ticker: str | None = None,
        min_ts: int | None = None,
        max_ts: int | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> FillPage:
        """
        Fetch matched trades (fills) from the portfolio.

        Args:
            ticker: Filter by market ticker
            min_ts: Filter trades after this timestamp (Unix seconds)
            max_ts: Filter trades before this timestamp
            limit: Number of results per page (max 200)
            cursor: Pagination cursor
        """
        params: dict[str, Any] = {"limit": min(limit, 200)}
        if ticker:
            params["ticker"] = ticker
        if min_ts is not None:
            params["min_ts"] = min_ts
        if max_ts is not None:
            params["max_ts"] = max_ts
        if cursor:
            params["cursor"] = cursor

        data = await self._auth_get("/portfolio/fills", params)
        return FillPage.model_validate(data)

    # ==================== Trading ====================

    async def create_order(
        self,
        ticker: str,
        side: Literal["yes", "no"] | OrderSide,
        action: Literal["buy", "sell"] | OrderAction,
        count: int,
        price: int,
        client_order_id: str | None = None,
        expiration_ts: int | None = None,
        dry_run: bool = False,
    ) -> OrderResponse:
        """
        Create a new limit order.

        Args:
            ticker: Market ticker
            side: "yes" or "no"
            action: "buy" or "sell"
            count: Number of contracts (must be > 0)
            price: Limit price in CENTS (1-99)
            client_order_id: Optional unique ID (generated if not provided)
            expiration_ts: Optional Unix timestamp for expiration
            dry_run: If True, validate and log order but do not execute

        Returns:
            OrderResponse with order_id and status
        """
        # 1-99 is Kalshi's valid trading range (0 and 100 are settled states)
        # See docs/_vendor-docs/kalshi-api-reference.md (Binary market math)
        if price < 1 or price > 99:
            raise ValueError("Price must be between 1 and 99 cents")

        if count <= 0:
            raise ValueError("Count must be positive")

        if not client_order_id:
            client_order_id = str(uuid.uuid4())

        payload = {
            "ticker": ticker,
            "action": action if isinstance(action, str) else action.value,
            "side": side if isinstance(side, str) else side.value,
            "count": count,
            "type": "limit",
            "yes_price": price,
            "client_order_id": client_order_id,
        }
        if expiration_ts:
            payload["expiration_ts"] = expiration_ts

        # Handle dry run mode
        if dry_run:
            logger.info(
                "DRY RUN: create_order - order validated but not executed",
                ticker=ticker,
                side=side if isinstance(side, str) else side.value,
                action=action if isinstance(action, str) else action.value,
                count=count,
                price=price,
                client_order_id=client_order_id,
                expiration_ts=expiration_ts,
            )
            return OrderResponse(
                order_id=f"dry-run-{client_order_id}",
                order_status="simulated",
            )

        # Acquire rate limit for WRITE
        await self._rate_limiter.acquire("POST", "/portfolio/orders")

        # Auth headers for POST
        headers = self._auth.get_headers("POST", self.API_PATH + "/portfolio/orders")

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(
                (RateLimitError, httpx.NetworkError, httpx.TimeoutException)
            ),
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=60),
            reraise=True,
        ):
            with attempt:
                response = await self._client.post(
                    "/portfolio/orders", json=payload, headers=headers
                )

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait_seconds = int(retry_after) if retry_after else None
                    raise RateLimitError("Rate limit exceeded", retry_after=wait_seconds)

                if response.status_code >= 400:
                    raise KalshiAPIError(response.status_code, response.text)

                data = response.json()
                return OrderResponse.model_validate(data["order"])

        raise AssertionError("AsyncRetrying should have returned or raised")  # pragma: no cover

    async def cancel_order(self, order_id: str) -> CancelOrderResponse:
        """Cancel an existing order."""
        path = f"/portfolio/orders/{order_id}"
        full_path = self.API_PATH + path

        await self._rate_limiter.acquire("DELETE", path)
        headers = self._auth.get_headers("DELETE", full_path)

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(
                (RateLimitError, httpx.NetworkError, httpx.TimeoutException)
            ),
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=60),
            reraise=True,
        ):
            with attempt:
                response = await self._client.delete(path, headers=headers)

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise RateLimitError(
                        "Rate limit exceeded",
                        retry_after=int(retry_after) if retry_after else None,
                    )

                if response.status_code >= 400:
                    raise KalshiAPIError(response.status_code, response.text)

                data = response.json()
                payload_obj = data.get("order", data) if isinstance(data, dict) else data
                if not isinstance(payload_obj, dict):
                    raise KalshiAPIError(
                        response.status_code,
                        "Unexpected cancel order response shape (expected object).",
                    )

                payload = dict(payload_obj)
                payload.setdefault("order_id", order_id)
                return CancelOrderResponse.model_validate(payload)

        raise AssertionError("AsyncRetrying should have returned or raised")  # pragma: no cover

    async def amend_order(
        self,
        order_id: str,
        price: int | None = None,
        count: int | None = None,
    ) -> OrderResponse:
        """Amend an existing order's price or quantity."""
        if price is None and count is None:
            raise ValueError("Must provide either price or count")

        if price is not None and (price < 1 or price > 99):
            raise ValueError("Price must be between 1 and 99 cents")

        if count is not None and count <= 0:
            raise ValueError("Count must be positive")

        path = f"/portfolio/orders/{order_id}/amend"
        full_path = self.API_PATH + path

        payload: dict[str, Any] = {"order_id": order_id}
        if price is not None:
            payload["yes_price"] = price
        if count is not None:
            payload["count"] = count

        await self._rate_limiter.acquire("POST", path)
        headers = self._auth.get_headers("POST", full_path)

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(
                (RateLimitError, httpx.NetworkError, httpx.TimeoutException)
            ),
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=60),
            reraise=True,
        ):
            with attempt:
                response = await self._client.post(path, json=payload, headers=headers)

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise RateLimitError(
                        "Rate limit exceeded",
                        retry_after=int(retry_after) if retry_after else None,
                    )

                if response.status_code >= 400:
                    raise KalshiAPIError(response.status_code, response.text)

                data = response.json()
                return OrderResponse.model_validate(data["order"])

        raise AssertionError("AsyncRetrying should have returned or raised")  # pragma: no cover
