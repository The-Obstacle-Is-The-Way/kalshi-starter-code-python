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
from kalshi_research.api.models.candlestick import (
    Candlestick,
    CandlestickResponse,
    EventCandlesticksResponse,
)
from kalshi_research.api.models.event import Event, EventMetadataResponse
from kalshi_research.api.models.exchange import (
    ExchangeAnnouncementsResponse,
    ExchangeScheduleResponse,
)
from kalshi_research.api.models.market import Market, MarketFilterStatus
from kalshi_research.api.models.multivariate import (
    GetMultivariateEventCollectionResponse,
    GetMultivariateEventCollectionsResponse,
    LookupTickersForMarketInMultivariateEventCollectionRequest,
    LookupTickersForMarketInMultivariateEventCollectionResponse,
    MultivariateEventCollection,
    TickerPair,
)
from kalshi_research.api.models.order import (
    CreateOrderRequest,
    OrderAction,
    OrderResponse,
    OrderSide,
)
from kalshi_research.api.models.order_group import (
    CreateOrderGroupResponse,
    EmptyResponse,
    OrderGroup,
    OrderGroupDetailResponse,
    OrderGroupsResponse,
)
from kalshi_research.api.models.orderbook import Orderbook
from kalshi_research.api.models.portfolio import (
    BatchCancelOrdersResponse,
    BatchCreateOrdersResponse,
    CancelOrderResponse,
    DecreaseOrderResponse,
    FillPage,
    GetOrderQueuePositionResponse,
    GetOrderQueuePositionsResponse,
    GetOrderResponse,
    GetPortfolioRestingOrderTotalValueResponse,
    Order,
    OrderPage,
    OrderQueuePosition,
    PortfolioBalance,
    PortfolioPosition,
    SettlementPage,
)
from kalshi_research.api.models.search import FiltersBySportsResponse, TagsByCategoriesResponse
from kalshi_research.api.models.series import (
    Series,
    SeriesListResponse,
    SeriesResponse,
)
from kalshi_research.api.models.trade import Trade
from kalshi_research.api.rate_limiter import RateLimiter, RateTier
from kalshi_research.constants import DEFAULT_ORDERBOOK_DEPTH

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

    # ==================== Markets ====================

    async def get_markets_page(
        self,
        status: MarketFilterStatus | str | None = None,
        event_ticker: str | None = None,
        series_ticker: str | None = None,
        tickers: list[str] | None = None,
        min_created_ts: int | None = None,
        max_created_ts: int | None = None,
        min_close_ts: int | None = None,
        max_close_ts: int | None = None,
        min_settled_ts: int | None = None,
        max_settled_ts: int | None = None,
        limit: int = 100,
        cursor: str | None = None,
        mve_filter: Literal["only", "exclude"] | None = None,
    ) -> tuple[list[Market], str | None]:
        """
        Fetch a single page of markets and return the next cursor (if any).

        Args:
            status: Filter by market status (unopened, open, closed, settled).
            event_ticker: Filter by event ticker.
            series_ticker: Filter by series ticker.
            tickers: Batch lookup by comma-separated market tickers.
            min_created_ts: Markets created after this Unix timestamp.
            max_created_ts: Markets created before this Unix timestamp.
            min_close_ts: Markets closing after this Unix timestamp.
            max_close_ts: Markets closing before this Unix timestamp.
            min_settled_ts: Markets settled after this Unix timestamp.
            max_settled_ts: Markets settled before this Unix timestamp.
            limit: Page size (max 1000).
            cursor: Pagination cursor.
            mve_filter: Filter for multivariate events ("only" or "exclude").

        Returns:
            Tuple of (markets, next_cursor).

        Raises:
            ValueError: If multiple timestamp filter families are used together.

        Note:
            Only one timestamp filter family may be used at a time:
            - created_ts: Compatible with status=unopened, open, or empty
            - close_ts: Compatible with status=closed or empty
            - settled_ts: Compatible with status=settled or empty
        """
        # Validate timestamp filter family exclusivity (OpenAPI constraint)
        ts_families_used = sum(
            [
                min_created_ts is not None or max_created_ts is not None,
                min_close_ts is not None or max_close_ts is not None,
                min_settled_ts is not None or max_settled_ts is not None,
            ]
        )
        if ts_families_used > 1:
            raise ValueError(
                "Only one timestamp filter family allowed at a time "
                "(created_ts OR close_ts OR settled_ts)"
            )

        # 1000 is Kalshi API max limit per page (see docs/_vendor-docs/kalshi-api-reference.md)
        params: dict[str, Any] = {"limit": min(limit, 1000)}
        if status:
            params["status"] = status.value if isinstance(status, MarketFilterStatus) else status
        if event_ticker:
            params["event_ticker"] = event_ticker
        if series_ticker:
            params["series_ticker"] = series_ticker
        if tickers:
            params["tickers"] = ",".join(tickers)
        # Add timestamp filters (consolidated to reduce branch count)
        ts_params = {
            "min_created_ts": min_created_ts,
            "max_created_ts": max_created_ts,
            "min_close_ts": min_close_ts,
            "max_close_ts": max_close_ts,
            "min_settled_ts": min_settled_ts,
            "max_settled_ts": max_settled_ts,
        }
        params.update({k: v for k, v in ts_params.items() if v is not None})
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
        if limit <= 0:
            return []

        markets: list[Market] = []
        cursor: str | None = None
        while len(markets) < limit:
            remaining = limit - len(markets)
            page_markets, cursor = await self.get_markets_page(
                status=status,
                event_ticker=event_ticker,
                series_ticker=series_ticker,
                limit=min(remaining, 1000),
                cursor=cursor,
                mve_filter=mve_filter,
            )
            markets.extend(page_markets)
            if cursor is None or not page_markets:
                break

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

    async def get_orderbook(self, ticker: str, depth: int = DEFAULT_ORDERBOOK_DEPTH) -> Orderbook:
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
        *,
        with_nested_markets: bool = False,
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
        if with_nested_markets:
            params["with_nested_markets"] = True

        data = await self._get("/events", params)
        events = [Event.model_validate(e) for e in data.get("events", [])]
        return events, data.get("cursor")

    async def get_events(
        self,
        status: MarketFilterStatus | str | None = None,
        series_ticker: str | None = None,
        limit: int = 100,
        *,
        with_nested_markets: bool = False,
    ) -> list[Event]:
        """Fetch events with optional filters."""
        events, _ = await self.get_events_page(
            status=status,
            series_ticker=series_ticker,
            limit=limit,
            with_nested_markets=with_nested_markets,
        )
        return events

    async def get_all_events(
        self,
        status: MarketFilterStatus | str | None = None,
        series_ticker: str | None = None,
        limit: int = 200,
        max_pages: int | None = None,
        *,
        with_nested_markets: bool = False,
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
                with_nested_markets=with_nested_markets,
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

    async def get_event_metadata(self, event_ticker: str) -> EventMetadataResponse:
        """Fetch event metadata for richer event context."""
        data = await self._get(f"/events/{event_ticker}/metadata")
        return EventMetadataResponse.model_validate(data)

    async def get_event_candlesticks(
        self,
        *,
        series_ticker: str,
        event_ticker: str,
        start_ts: int | None = None,
        end_ts: int | None = None,
        period_interval: int = 60,
    ) -> EventCandlesticksResponse:
        """
        Fetch event-level candlestick data (multiple markets aligned by index).

        Args:
            series_ticker: Parent series ticker.
            event_ticker: Event ticker.
            start_ts: Optional start timestamp (Unix seconds).
            end_ts: Optional end timestamp (Unix seconds).
            period_interval: Candle period in minutes (1, 60, or 1440).
        """
        params: dict[str, Any] = {"period_interval": period_interval}
        if start_ts is not None:
            params["start_ts"] = start_ts
        if end_ts is not None:
            params["end_ts"] = end_ts

        data = await self._get(
            f"/series/{series_ticker}/events/{event_ticker}/candlesticks",
            params,
        )
        return EventCandlesticksResponse.model_validate(data)

    async def get_multivariate_events_page(
        self,
        limit: int = 200,
        cursor: str | None = None,
    ) -> tuple[list[Event], str | None]:
        """
        Fetch a single page of multivariate events and return the next cursor (if any).

        Notes:
            Kalshi excludes MVEs from `GET /events`; use `GET /events/multivariate` for MVEs.
            See: docs/_vendor-docs/kalshi-api-reference.md
        """
        params: dict[str, Any] = {"limit": min(limit, 200)}
        if cursor:
            params["cursor"] = cursor

        data = await self._get("/events/multivariate", params)
        events = [Event.model_validate(e) for e in data.get("events", [])]
        return events, data.get("cursor")

    async def get_multivariate_events(self, limit: int = 200) -> list[Event]:
        """Fetch multivariate events (MVEs)."""
        events, _ = await self.get_multivariate_events_page(limit=limit)
        return events

    async def get_all_multivariate_events(
        self,
        limit: int = 200,
        max_pages: int | None = None,
    ) -> AsyncIterator[Event]:
        """
        Iterate through ALL multivariate events with automatic pagination.

        Args:
            limit: Page size (max 200 for events/multivariate endpoint)
            max_pages: Optional safety limit. None = iterate until exhausted.

        Yields:
            Event objects
        """
        cursor: str | None = None
        pages = 0
        while True:
            events, cursor = await self.get_multivariate_events_page(
                limit=limit,
                cursor=cursor,
            )

            for event in events:
                yield event

            if not cursor or not events:
                break

            pages += 1

            if max_pages is not None and pages >= max_pages:
                logger.warning(
                    "Pagination truncated: reached max_pages but cursor still present. "
                    "Data may be incomplete. Set max_pages=None for full iteration.",
                    max_pages=max_pages,
                )
                break

    # ==================== Multivariate Collections ====================

    async def get_multivariate_event_collections(
        self,
        *,
        status: str | None = None,
        associated_event_ticker: str | None = None,
        series_ticker: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> GetMultivariateEventCollectionsResponse:
        """
        List multivariate event collections with optional filters.

        Args:
            status: Optional filter (`unopened`, `open`, `closed`).
            associated_event_ticker: Optional associated event filter.
            series_ticker: Optional series filter.
            limit: Page size (1-200).
            cursor: Pagination cursor from a prior response.
        """
        params: dict[str, Any] = {"limit": max(1, min(limit, 200))}
        if status is not None:
            params["status"] = status
        if associated_event_ticker is not None:
            params["associated_event_ticker"] = associated_event_ticker
        if series_ticker is not None:
            params["series_ticker"] = series_ticker
        if cursor is not None:
            params["cursor"] = cursor

        data = await self._get("/multivariate_event_collections", params)
        return GetMultivariateEventCollectionsResponse.model_validate(data)

    async def get_multivariate_event_collection(
        self, collection_ticker: str
    ) -> MultivariateEventCollection:
        """Fetch a single multivariate event collection by ticker."""
        data = await self._get(f"/multivariate_event_collections/{collection_ticker}")
        parsed = GetMultivariateEventCollectionResponse.model_validate(data)
        return parsed.multivariate_contract

    # ==================== Search & Series ====================

    async def get_tags_by_categories(self) -> dict[str, list[str]]:
        """Fetch category->tags mapping for series discovery."""
        data = await self._get("/search/tags_by_categories")
        parsed = TagsByCategoriesResponse.model_validate(data)
        return {
            category: (tags if tags is not None else [])
            for category, tags in parsed.tags_by_categories.items()
        }

    async def get_filters_by_sport(self) -> FiltersBySportsResponse:
        """Fetch sport-specific filters for discovery UIs."""
        data = await self._get("/search/filters_by_sport")
        return FiltersBySportsResponse.model_validate(data)

    async def get_series_list(
        self,
        *,
        category: str | None = None,
        tags: str | None = None,
        include_product_metadata: bool = False,
        include_volume: bool = False,
    ) -> list[Series]:
        """
        List available series with optional filters.

        This is the intended Kalshi browse pattern:
        `/search/tags_by_categories` -> `/series` -> `/markets?series_ticker=...`.
        """
        params: dict[str, Any] = {}
        if category is not None:
            params["category"] = category
        if tags is not None:
            params["tags"] = tags
        if include_product_metadata:
            params["include_product_metadata"] = True
        if include_volume:
            params["include_volume"] = True

        data = await self._get("/series", params or None)
        return SeriesListResponse.model_validate(data).series

    async def get_series(
        self,
        series_ticker: str,
        *,
        include_volume: bool = False,
    ) -> Series:
        """Fetch a single series by ticker."""
        params: dict[str, Any] = {}
        if include_volume:
            params["include_volume"] = True
        data = await self._get(f"/series/{series_ticker}", params or None)
        return SeriesResponse.model_validate(data).series

    # ==================== Exchange ====================

    async def get_exchange_status(self) -> dict[str, Any]:
        """Check if exchange is operational."""
        return await self._get("/exchange/status")

    async def get_exchange_schedule(self) -> ExchangeScheduleResponse:
        """Fetch the exchange schedule (standard hours + maintenance windows)."""
        data = await self._get("/exchange/schedule")
        return ExchangeScheduleResponse.model_validate(data)

    async def get_exchange_announcements(self) -> ExchangeAnnouncementsResponse:
        """Fetch exchange-wide announcements."""
        data = await self._get("/exchange/announcements")
        return ExchangeAnnouncementsResponse.model_validate(data)


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
        await self.aclose()

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

    # ==================== Multivariate Collections ====================

    async def lookup_multivariate_event_collection_tickers(
        self,
        collection_ticker: str,
        selected_markets: list[TickerPair],
    ) -> LookupTickersForMarketInMultivariateEventCollectionResponse:
        """
        Lookup tickers for a multivariate market in a collection.

        Args:
            collection_ticker: Multivariate event collection ticker.
            selected_markets: Underlying market selections.

        Returns:
            The derived event and market tickers for the selected markets.

        Raises:
            ValueError: If `selected_markets` is empty.
        """
        if not selected_markets:
            raise ValueError("selected_markets must be non-empty")

        path = f"/multivariate_event_collections/{collection_ticker}/lookup"
        full_path = self.API_PATH + path
        payload = LookupTickersForMarketInMultivariateEventCollectionRequest(
            selected_markets=selected_markets
        ).model_dump(mode="json")

        await self._rate_limiter.acquire("PUT", path)
        headers = self._auth.get_headers("PUT", full_path)

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(
                (RateLimitError, httpx.NetworkError, httpx.TimeoutException)
            ),
            stop=stop_after_attempt(self._max_retries),
            wait=_wait_with_retry_after,
            reraise=True,
        ):
            with attempt:
                response = await self._client.put(path, json=payload, headers=headers)

                if response.status_code == 429:
                    retry_after: int | None = None
                    retry_after_header = response.headers.get("Retry-After")
                    if retry_after_header is not None:
                        try:
                            retry_after = int(retry_after_header)
                        except ValueError:
                            retry_after = None
                    raise RateLimitError(
                        "Rate limit exceeded",
                        retry_after=retry_after,
                    )

                if response.status_code >= 400:
                    raise KalshiAPIError(response.status_code, response.text)

                data = response.json() if response.content else {}
                if not isinstance(data, dict):
                    raise KalshiAPIError(
                        response.status_code,
                        "Unexpected multivariate lookup response shape (expected object).",
                    )
                return LookupTickersForMarketInMultivariateEventCollectionResponse.model_validate(
                    data
                )

        raise AssertionError("AsyncRetrying should have returned or raised")  # pragma: no cover

    async def get_balance(self) -> PortfolioBalance:
        """Get account balance."""
        data = await self._auth_get("/portfolio/balance")
        return PortfolioBalance.model_validate(data)

    async def get_positions(self) -> list[PortfolioPosition]:
        """Get current market positions."""
        data = await self._auth_get("/portfolio/positions")
        # Kalshi returns `market_positions` (and `event_positions` for event-level aggregation)
        raw = data.get("market_positions", [])
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

    async def get_settlements(
        self,
        ticker: str | None = None,
        event_ticker: str | None = None,
        min_ts: int | None = None,
        max_ts: int | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> SettlementPage:
        """
        Fetch settlement history from the portfolio.

        Args:
            ticker: Filter by market ticker
            event_ticker: Filter by event ticker (comma-separated list supported by API)
            min_ts: Filter settlements after this timestamp (Unix seconds)
            max_ts: Filter settlements before this timestamp
            limit: Number of results per page (max 200)
            cursor: Pagination cursor
        """
        params: dict[str, Any] = {"limit": min(limit, 200)}
        if ticker:
            params["ticker"] = ticker
        if event_ticker:
            params["event_ticker"] = event_ticker
        if min_ts is not None:
            params["min_ts"] = min_ts
        if max_ts is not None:
            params["max_ts"] = max_ts
        if cursor:
            params["cursor"] = cursor

        data = await self._auth_get("/portfolio/settlements", params)
        return SettlementPage.model_validate(data)

    # ==================== Trading ====================

    async def get_order(self, order_id: str) -> Order:
        """Fetch a single order by order ID."""
        data = await self._auth_get(f"/portfolio/orders/{order_id}")
        parsed = GetOrderResponse.model_validate(data)
        return parsed.order

    async def batch_create_orders(
        self,
        orders: list[CreateOrderRequest],
        *,
        dry_run: bool = False,
    ) -> BatchCreateOrdersResponse:
        """Create up to 20 orders in a single API request."""
        if not orders:
            raise ValueError("orders must be non-empty")
        if len(orders) > 20:
            raise ValueError("Maximum 20 orders per batch request")

        if dry_run:
            logger.info("DRY RUN: batch_create_orders - request validated but not executed")
            return BatchCreateOrdersResponse(orders=[])

        path = "/portfolio/orders/batched"
        full_path = self.API_PATH + path
        payload: dict[str, Any] = {
            "orders": [o.model_dump(mode="json", exclude_none=True) for o in orders]
        }

        await self._rate_limiter.acquire("POST", path, batch_size=len(orders))
        headers = self._auth.get_headers("POST", full_path)

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(
                (RateLimitError, httpx.NetworkError, httpx.TimeoutException)
            ),
            stop=stop_after_attempt(self._max_retries),
            wait=_wait_with_retry_after,
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
                if not isinstance(data, dict):
                    raise KalshiAPIError(
                        response.status_code,
                        "Unexpected batch create response shape (expected object).",
                    )
                return BatchCreateOrdersResponse.model_validate(data)

        raise AssertionError("AsyncRetrying should have returned or raised")  # pragma: no cover

    async def batch_cancel_orders(
        self,
        order_ids: list[str],
        *,
        dry_run: bool = False,
    ) -> BatchCancelOrdersResponse:
        """Cancel up to 20 orders in a single API request."""
        if not order_ids:
            raise ValueError("order_ids must be non-empty")
        if len(order_ids) > 20:
            raise ValueError("Maximum 20 order_ids per batch request")

        if dry_run:
            logger.info("DRY RUN: batch_cancel_orders - request validated but not executed")
            return BatchCancelOrdersResponse(orders=[])

        path = "/portfolio/orders/batched"
        full_path = self.API_PATH + path
        payload: dict[str, Any] = {"ids": order_ids}

        await self._rate_limiter.acquire("DELETE", path, batch_size=len(order_ids))
        headers = self._auth.get_headers("DELETE", full_path)

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(
                (RateLimitError, httpx.NetworkError, httpx.TimeoutException)
            ),
            stop=stop_after_attempt(self._max_retries),
            wait=_wait_with_retry_after,
            reraise=True,
        ):
            with attempt:
                response = await self._client.request("DELETE", path, json=payload, headers=headers)

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise RateLimitError(
                        "Rate limit exceeded",
                        retry_after=int(retry_after) if retry_after else None,
                    )

                if response.status_code >= 400:
                    raise KalshiAPIError(response.status_code, response.text)

                data = response.json()
                if not isinstance(data, dict):
                    raise KalshiAPIError(
                        response.status_code,
                        "Unexpected batch cancel response shape (expected object).",
                    )
                return BatchCancelOrdersResponse.model_validate(data)

        raise AssertionError("AsyncRetrying should have returned or raised")  # pragma: no cover

    async def decrease_order(
        self,
        order_id: str,
        *,
        reduce_by: int | None = None,
        reduce_to: int | None = None,
        dry_run: bool = False,
    ) -> Order:
        """Decrease an order's remaining size (preserves queue position)."""
        if reduce_by is None and reduce_to is None:
            raise ValueError("Must provide reduce_by or reduce_to")
        if reduce_by is not None and reduce_to is not None:
            raise ValueError("Provide only one of reduce_by or reduce_to")
        if reduce_by is not None and reduce_by <= 0:
            raise ValueError("reduce_by must be positive")
        if reduce_to is not None and reduce_to < 0:
            raise ValueError("reduce_to must be non-negative")

        if dry_run:
            logger.info(
                "DRY RUN: decrease_order - request validated but not executed", order_id=order_id
            )
            return await self.get_order(order_id)

        path = f"/portfolio/orders/{order_id}/decrease"
        full_path = self.API_PATH + path
        payload: dict[str, Any] = {}
        if reduce_by is not None:
            payload["reduce_by"] = reduce_by
        if reduce_to is not None:
            payload["reduce_to"] = reduce_to

        await self._rate_limiter.acquire("POST", path)
        headers = self._auth.get_headers("POST", full_path)

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(
                (RateLimitError, httpx.NetworkError, httpx.TimeoutException)
            ),
            stop=stop_after_attempt(self._max_retries),
            wait=_wait_with_retry_after,
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
                if not isinstance(data, dict):
                    raise KalshiAPIError(
                        response.status_code,
                        "Unexpected decrease response shape (expected object).",
                    )
                parsed = DecreaseOrderResponse.model_validate(data)
                return parsed.order

        raise AssertionError("AsyncRetrying should have returned or raised")  # pragma: no cover

    async def get_order_queue_position(self, order_id: str) -> int:
        """Get the queue position for a resting order."""
        data = await self._auth_get(f"/portfolio/orders/{order_id}/queue_position")
        parsed = GetOrderQueuePositionResponse.model_validate(data)
        return parsed.queue_position

    async def get_orders_queue_positions(
        self,
        *,
        market_tickers: list[str] | None = None,
        event_ticker: str | None = None,
    ) -> list[OrderQueuePosition]:
        """Get queue positions for all resting orders (optionally filtered).

        Note: API requires at least one of market_tickers or event_ticker.
        """
        params: dict[str, Any] = {}
        if market_tickers:
            params["market_tickers"] = ",".join(market_tickers)
        if event_ticker is not None:
            params["event_ticker"] = event_ticker

        data = await self._auth_get("/portfolio/orders/queue_positions", params or None)
        parsed = GetOrderQueuePositionsResponse.model_validate(data)
        return parsed.queue_positions or []

    async def get_total_resting_order_value(self) -> int:
        """Get the total value of all resting orders in cents."""
        data = await self._auth_get("/portfolio/summary/total_resting_order_value")
        parsed = GetPortfolioRestingOrderTotalValueResponse.model_validate(data)
        return parsed.total_resting_order_value

    # ==================== Order Groups ====================

    async def get_order_groups(self) -> list[OrderGroup]:
        """List order groups for the authenticated user."""
        data = await self._auth_get("/portfolio/order_groups")
        return OrderGroupsResponse.model_validate(data).order_groups

    async def create_order_group(self, *, contracts_limit: int) -> str:
        """
        Create a new order group with a matched-contracts limit.

        Args:
            contracts_limit: Maximum number of contracts that can be matched within this group.

        Returns:
            The created order group ID.
        """
        if contracts_limit <= 0:
            raise ValueError("contracts_limit must be positive")

        path = "/portfolio/order_groups/create"
        full_path = self.API_PATH + path
        payload = {"contracts_limit": contracts_limit}

        await self._rate_limiter.acquire("POST", path)
        headers = self._auth.get_headers("POST", full_path)

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(
                (RateLimitError, httpx.NetworkError, httpx.TimeoutException)
            ),
            stop=stop_after_attempt(self._max_retries),
            wait=_wait_with_retry_after,
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
                if not isinstance(data, dict):
                    raise KalshiAPIError(
                        response.status_code,
                        "Unexpected create order group response shape (expected object).",
                    )
                parsed = CreateOrderGroupResponse.model_validate(data)
                return parsed.order_group_id

        raise AssertionError("AsyncRetrying should have returned or raised")  # pragma: no cover

    async def get_order_group(self, order_group_id: str) -> OrderGroupDetailResponse:
        """Fetch a single order group detail by ID."""
        data = await self._auth_get(f"/portfolio/order_groups/{order_group_id}")
        return OrderGroupDetailResponse.model_validate(data)

    async def reset_order_group(self, order_group_id: str) -> None:
        """Reset an order group, allowing new orders after a contracts limit is hit."""
        path = f"/portfolio/order_groups/{order_group_id}/reset"
        full_path = self.API_PATH + path

        await self._rate_limiter.acquire("PUT", path)
        headers = self._auth.get_headers("PUT", full_path)

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(
                (RateLimitError, httpx.NetworkError, httpx.TimeoutException)
            ),
            stop=stop_after_attempt(self._max_retries),
            wait=_wait_with_retry_after,
            reraise=True,
        ):
            with attempt:
                response = await self._client.put(path, json={}, headers=headers)

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise RateLimitError(
                        "Rate limit exceeded",
                        retry_after=int(retry_after) if retry_after else None,
                    )

                if response.status_code >= 400:
                    raise KalshiAPIError(response.status_code, response.text)

                payload = response.json() if response.content else {}
                if not isinstance(payload, dict):
                    raise KalshiAPIError(
                        response.status_code,
                        "Unexpected reset order group response shape (expected object).",
                    )
                EmptyResponse.model_validate(payload)
                return None

        raise AssertionError("AsyncRetrying should have returned or raised")  # pragma: no cover

    async def delete_order_group(self, order_group_id: str) -> None:
        """Delete an order group and cancel all orders within it."""
        path = f"/portfolio/order_groups/{order_group_id}"
        full_path = self.API_PATH + path

        await self._rate_limiter.acquire("DELETE", path)
        headers = self._auth.get_headers("DELETE", full_path)

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(
                (RateLimitError, httpx.NetworkError, httpx.TimeoutException)
            ),
            stop=stop_after_attempt(self._max_retries),
            wait=_wait_with_retry_after,
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

                payload = response.json() if response.content else {}
                if not isinstance(payload, dict):
                    raise KalshiAPIError(
                        response.status_code,
                        "Unexpected delete order group response shape (expected object).",
                    )
                EmptyResponse.model_validate(payload)
                return None

        raise AssertionError("AsyncRetrying should have returned or raised")  # pragma: no cover

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
        *,
        reduce_only: bool | None = None,
        post_only: bool | None = None,
        time_in_force: Literal[
            "fill_or_kill",
            "good_till_canceled",
            "immediate_or_cancel",
        ]
        | None = None,
        buy_max_cost: int | None = None,
        cancel_order_on_pause: bool | None = None,
        self_trade_prevention_type: Literal["taker_at_cross", "maker"] | None = None,
        order_group_id: str | None = None,
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
            reduce_only: Optional exchange-enforced safety. When true, only reduces an existing
                position.
            post_only: Optional maker-only flag. When true, order will not cross the spread.
            time_in_force: Optional order persistence (`fill_or_kill`, `good_till_canceled`,
                `immediate_or_cancel`).
            buy_max_cost: Optional max cost in cents; enables Fill-or-Kill behavior.
            cancel_order_on_pause: Optional auto-cancel flag if trading is paused.
            self_trade_prevention_type: Optional self-trade prevention mode.
            order_group_id: Optional order group identifier for linked order management.
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
        optional_fields: dict[str, object] = {
            "expiration_ts": expiration_ts,
            "reduce_only": reduce_only,
            "post_only": post_only,
            "time_in_force": time_in_force,
            "buy_max_cost": buy_max_cost,
            "cancel_order_on_pause": cancel_order_on_pause,
            "self_trade_prevention_type": self_trade_prevention_type,
            "order_group_id": order_group_id,
        }
        payload.update({key: value for key, value in optional_fields.items() if value is not None})

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
                reduce_only=reduce_only,
                post_only=post_only,
                time_in_force=time_in_force,
                buy_max_cost=buy_max_cost,
                cancel_order_on_pause=cancel_order_on_pause,
                self_trade_prevention_type=self_trade_prevention_type,
                order_group_id=order_group_id,
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

    async def cancel_order(self, order_id: str, dry_run: bool = False) -> CancelOrderResponse:
        """
        Cancel an existing order.

        Args:
            order_id: The order ID to cancel
            dry_run: If True, validate and log but do not execute the cancellation

        Returns:
            CancelOrderResponse with order status
        """
        # Handle dry run mode
        if dry_run:
            logger.info(
                "DRY RUN: cancel_order - cancellation validated but not executed",
                order_id=order_id,
            )
            return CancelOrderResponse(
                order_id=f"dry-run-{order_id}",
                status="simulated",
            )

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
                if isinstance(data, dict) and "reduced_by" in data and "reduced_by" not in payload:
                    payload["reduced_by"] = data["reduced_by"]
                payload.setdefault("order_id", order_id)
                return CancelOrderResponse.model_validate(payload)

        raise AssertionError("AsyncRetrying should have returned or raised")  # pragma: no cover

    async def amend_order(
        self,
        order_id: str,
        ticker: str,
        side: Literal["yes", "no"] | OrderSide,
        action: Literal["buy", "sell"] | OrderAction,
        client_order_id: str,
        updated_client_order_id: str,
        *,
        price: int | None = None,
        price_dollars: str | None = None,
        count: int | None = None,
        dry_run: bool = False,
    ) -> OrderResponse:
        """
        Amend an existing order's price or quantity.

        Args:
            order_id: The order ID to amend
            ticker: Market ticker
            side: "yes" or "no"
            action: "buy" or "sell"
            client_order_id: Original client_order_id used when creating the order
            updated_client_order_id: New unique client_order_id for the amended order
            price: New price in cents (1-99)
            price_dollars: New price in dollars (e.g., "0.5500")
            count: New quantity (must be positive)
            dry_run: If True, validate and log but do not execute the amendment

        Returns:
            OrderResponse with updated order status
        """
        if not updated_client_order_id:
            raise ValueError("updated_client_order_id must be provided")

        if price is not None and price_dollars is not None:
            raise ValueError("Provide only one of price or price_dollars")

        if price is None and price_dollars is None and count is None:
            raise ValueError("Must provide either price/price_dollars or count")

        if price is not None and (price < 1 or price > 99):
            raise ValueError("Price must be between 1 and 99 cents")

        if count is not None and count <= 0:
            raise ValueError("Count must be positive")

        side_value = side if isinstance(side, str) else side.value
        action_value = action if isinstance(action, str) else action.value

        # Handle dry run mode
        if dry_run:
            logger.info(
                "DRY RUN: amend_order - amendment validated but not executed",
                order_id=order_id,
                ticker=ticker,
                side=side_value,
                action=action_value,
                client_order_id=client_order_id,
                updated_client_order_id=updated_client_order_id,
                price=price,
                price_dollars=price_dollars,
                count=count,
            )
            return OrderResponse(
                order_id=f"dry-run-{order_id}",
                order_status="simulated",
            )

        path = f"/portfolio/orders/{order_id}/amend"
        full_path = self.API_PATH + path

        payload: dict[str, Any] = {
            "ticker": ticker,
            "side": side_value,
            "action": action_value,
            "client_order_id": client_order_id,
            "updated_client_order_id": updated_client_order_id,
        }
        if price is not None:
            price_key = "yes_price" if side_value == "yes" else "no_price"
            payload[price_key] = price
        if price_dollars is not None:
            dollars_key = "yes_price_dollars" if side_value == "yes" else "no_price_dollars"
            payload[dollars_key] = price_dollars
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
