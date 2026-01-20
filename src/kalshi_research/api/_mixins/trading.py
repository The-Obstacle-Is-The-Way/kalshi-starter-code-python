"""Trading endpoint mixin (authenticated, write operations)."""

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

from kalshi_research.api.exceptions import KalshiAPIError, RateLimitError
from kalshi_research.api.models.multivariate import (
    LookupTickersForMarketInMultivariateEventCollectionRequest,
    LookupTickersForMarketInMultivariateEventCollectionResponse,
    TickerPair,
)
from kalshi_research.api.models.portfolio import (
    BatchCancelOrdersResponse,
    BatchCreateOrdersResponse,
    DecreaseOrderResponse,
    GetOrderQueuePositionResponse,
    GetOrderQueuePositionsResponse,
    GetPortfolioRestingOrderTotalValueResponse,
    Order,
    OrderQueuePosition,
)

if TYPE_CHECKING:
    from kalshi_research.api.auth import KalshiAuth
    from kalshi_research.api.models.order import CreateOrderRequest
    from kalshi_research.api.rate_limiter import RateLimiter


logger = structlog.get_logger()


def _parse_retry_after(header_value: str | None) -> int | None:
    """Safely parse Retry-After header value, returning None if invalid."""
    if header_value is None:
        return None
    try:
        return int(header_value)
    except ValueError:
        return None


def _wait_with_retry_after_trading(retry_state: Any) -> float:
    """Wait using Retry-After header if available, else exponential backoff."""
    _retry_wait = wait_exponential(multiplier=1, min=1, max=60)
    outcome = retry_state.outcome
    if outcome is not None:
        exc = outcome.exception()
        if isinstance(exc, RateLimitError) and exc.retry_after is not None:
            return float(exc.retry_after)
    return float(_retry_wait(retry_state))


class TradingMixin:
    """Mixin providing trading endpoints (authenticated, write operations)."""

    # Attributes/methods expected from composing class (not implemented here)
    API_PATH: str
    _client: httpx.AsyncClient
    _max_retries: int
    _rate_limiter: RateLimiter
    _auth: KalshiAuth
    _auth_get: Any  # Provided by KalshiClient
    get_order: Any  # Provided by PortfolioMixin

    async def lookup_multivariate_event_collection_tickers(
        self, collection_ticker: str, selected_markets: list[TickerPair]
    ) -> LookupTickersForMarketInMultivariateEventCollectionResponse:
        """Lookup tickers for a multivariate market in a collection."""
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
            wait=_wait_with_retry_after_trading,
            reraise=True,
        ):
            with attempt:
                response = await self._client.put(path, json=payload, headers=headers)
                if response.status_code == 429:
                    raise RateLimitError(
                        "Rate limit exceeded",
                        retry_after=_parse_retry_after(response.headers.get("Retry-After")),
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

    async def batch_create_orders(
        self, orders: list[CreateOrderRequest], *, dry_run: bool = False
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
        payload: dict[str, Any] = {
            "orders": [o.model_dump(mode="json", exclude_none=True) for o in orders]
        }
        await self._rate_limiter.acquire("POST", path, batch_size=len(orders))
        headers = self._auth.get_headers("POST", self.API_PATH + path)

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(
                (RateLimitError, httpx.NetworkError, httpx.TimeoutException)
            ),
            stop=stop_after_attempt(self._max_retries),
            wait=_wait_with_retry_after_trading,
            reraise=True,
        ):
            with attempt:
                response = await self._client.post(path, json=payload, headers=headers)
                if response.status_code == 429:
                    raise RateLimitError(
                        "Rate limit exceeded",
                        retry_after=_parse_retry_after(response.headers.get("Retry-After")),
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
        self, order_ids: list[str], *, dry_run: bool = False
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
        payload: dict[str, Any] = {"ids": order_ids}
        await self._rate_limiter.acquire("DELETE", path, batch_size=len(order_ids))
        headers = self._auth.get_headers("DELETE", self.API_PATH + path)

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(
                (RateLimitError, httpx.NetworkError, httpx.TimeoutException)
            ),
            stop=stop_after_attempt(self._max_retries),
            wait=_wait_with_retry_after_trading,
            reraise=True,
        ):
            with attempt:
                response = await self._client.request("DELETE", path, json=payload, headers=headers)
                if response.status_code == 429:
                    raise RateLimitError(
                        "Rate limit exceeded",
                        retry_after=_parse_retry_after(response.headers.get("Retry-After")),
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
            logger.info("DRY RUN: decrease_order - validated but not executed", order_id=order_id)
            order: Order = await self.get_order(order_id)
            return order

        path = f"/portfolio/orders/{order_id}/decrease"
        payload: dict[str, Any] = {}
        if reduce_by is not None:
            payload["reduce_by"] = reduce_by
        if reduce_to is not None:
            payload["reduce_to"] = reduce_to
        await self._rate_limiter.acquire("POST", path)
        headers = self._auth.get_headers("POST", self.API_PATH + path)

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(
                (RateLimitError, httpx.NetworkError, httpx.TimeoutException)
            ),
            stop=stop_after_attempt(self._max_retries),
            wait=_wait_with_retry_after_trading,
            reraise=True,
        ):
            with attempt:
                response = await self._client.post(path, json=payload, headers=headers)
                if response.status_code == 429:
                    raise RateLimitError(
                        "Rate limit exceeded",
                        retry_after=_parse_retry_after(response.headers.get("Retry-After")),
                    )
                if response.status_code >= 400:
                    raise KalshiAPIError(response.status_code, response.text)
                data = response.json()
                if not isinstance(data, dict):
                    raise KalshiAPIError(
                        response.status_code,
                        "Unexpected decrease response shape (expected object).",
                    )
                return DecreaseOrderResponse.model_validate(data).order
        raise AssertionError("AsyncRetrying should have returned or raised")  # pragma: no cover

    async def get_order_queue_position(self, order_id: str) -> int:
        """Get the queue position for a resting order."""
        data = await self._auth_get(f"/portfolio/orders/{order_id}/queue_position")
        return GetOrderQueuePositionResponse.model_validate(data).queue_position

    async def get_orders_queue_positions(
        self, *, market_tickers: list[str] | None = None, event_ticker: str | None = None
    ) -> list[OrderQueuePosition]:
        """Get queue positions for all resting orders (optionally filtered)."""
        params: dict[str, Any] = {}
        if market_tickers:
            params["market_tickers"] = ",".join(market_tickers)
        if event_ticker is not None:
            params["event_ticker"] = event_ticker
        data = await self._auth_get("/portfolio/orders/queue_positions", params or None)
        return GetOrderQueuePositionsResponse.model_validate(data).queue_positions or []

    async def get_total_resting_order_value(self) -> int:
        """Get the total value of all resting orders in cents."""
        data = await self._auth_get("/portfolio/summary/total_resting_order_value")
        return GetPortfolioRestingOrderTotalValueResponse.model_validate(
            data
        ).total_resting_order_value
