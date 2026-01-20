"""Order create/cancel/amend endpoint mixin (authenticated)."""

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

from kalshi_research.api.exceptions import KalshiAPIError, RateLimitError
from kalshi_research.api.models.order import OrderAction, OrderResponse, OrderSide
from kalshi_research.api.models.portfolio import CancelOrderResponse

if TYPE_CHECKING:
    from kalshi_research.api.auth import KalshiAuth
    from kalshi_research.api.rate_limiter import RateLimiter


logger = structlog.get_logger()


class OrdersMixin:
    """Mixin providing order create/cancel/amend endpoints (authenticated)."""

    # Attributes expected from composing class (not implemented here)
    API_PATH: str
    _client: httpx.AsyncClient
    _max_retries: int
    _rate_limiter: RateLimiter
    _auth: KalshiAuth

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
        time_in_force: Literal["fill_or_kill", "good_till_canceled", "immediate_or_cancel"]
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
            reduce_only: Optional exchange-enforced safety
            post_only: Optional maker-only flag
            time_in_force: Optional order persistence
            buy_max_cost: Optional max cost in cents
            cancel_order_on_pause: Optional auto-cancel flag
            self_trade_prevention_type: Optional self-trade prevention mode
            order_group_id: Optional order group identifier
            dry_run: If True, validate and log order but do not execute
        """
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

        if dry_run:
            logger.info(
                "DRY RUN: create_order - order validated but not executed",
                ticker=ticker,
                side=side if isinstance(side, str) else side.value,
                action=action if isinstance(action, str) else action.value,
                count=count,
                price=price,
                client_order_id=client_order_id,
            )
            return OrderResponse(order_id=f"dry-run-{client_order_id}", order_status="simulated")

        await self._rate_limiter.acquire("POST", "/portfolio/orders")
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
                    raise RateLimitError(
                        "Rate limit exceeded", retry_after=int(retry_after) if retry_after else None
                    )
                if response.status_code >= 400:
                    raise KalshiAPIError(response.status_code, response.text)
                data = response.json()
                return OrderResponse.model_validate(data["order"])
        raise AssertionError("AsyncRetrying should have returned or raised")  # pragma: no cover

    async def cancel_order(self, order_id: str, dry_run: bool = False) -> CancelOrderResponse:
        """Cancel an existing order."""
        if dry_run:
            logger.info(
                "DRY RUN: cancel_order - cancellation validated but not executed",
                order_id=order_id,
            )
            return CancelOrderResponse(order_id=f"dry-run-{order_id}", status="simulated")

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
                        "Rate limit exceeded", retry_after=int(retry_after) if retry_after else None
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
                result = dict(payload_obj)
                if isinstance(data, dict) and "reduced_by" in data and "reduced_by" not in result:
                    result["reduced_by"] = data["reduced_by"]
                result.setdefault("order_id", order_id)
                return CancelOrderResponse.model_validate(result)
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
        """Amend an existing order's price or quantity."""
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

        if dry_run:
            logger.info(
                "DRY RUN: amend_order - amendment validated but not executed",
                order_id=order_id,
                ticker=ticker,
                side=side_value,
                action=action_value,
            )
            return OrderResponse(order_id=f"dry-run-{order_id}", order_status="simulated")

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
                        "Rate limit exceeded", retry_after=int(retry_after) if retry_after else None
                    )
                if response.status_code >= 400:
                    raise KalshiAPIError(response.status_code, response.text)
                data = response.json()
                return OrderResponse.model_validate(data["order"])
        raise AssertionError("AsyncRetrying should have returned or raised")  # pragma: no cover
