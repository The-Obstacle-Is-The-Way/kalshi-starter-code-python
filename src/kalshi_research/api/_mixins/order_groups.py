"""Order group endpoint mixin (authenticated)."""

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
from kalshi_research.api.models.order_group import (
    CreateOrderGroupResponse,
    EmptyResponse,
    OrderGroup,
    OrderGroupDetailResponse,
    OrderGroupsResponse,
)

if TYPE_CHECKING:
    from kalshi_research.api.auth import KalshiAuth
    from kalshi_research.api.rate_limiter import RateLimiter


logger = structlog.get_logger()


def _wait_with_retry_after_order_groups(retry_state: Any) -> float:
    """Wait using Retry-After header if available, else exponential backoff."""
    _retry_wait = wait_exponential(multiplier=1, min=1, max=60)
    outcome = retry_state.outcome
    if outcome is not None:
        exc = outcome.exception()
        if isinstance(exc, RateLimitError) and exc.retry_after is not None:
            return float(exc.retry_after)
    return float(_retry_wait(retry_state))


class OrderGroupsMixin:
    """Mixin providing order group endpoints (authenticated)."""

    # Attributes/methods expected from composing class (not implemented here)
    API_PATH: str
    _client: httpx.AsyncClient
    _max_retries: int
    _rate_limiter: RateLimiter
    _auth: KalshiAuth
    _auth_get: Any  # Provided by KalshiClient

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
            wait=_wait_with_retry_after_order_groups,
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
            wait=_wait_with_retry_after_order_groups,
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

                payload_data = response.json() if response.content else {}
                if not isinstance(payload_data, dict):
                    raise KalshiAPIError(
                        response.status_code,
                        "Unexpected reset order group response shape (expected object).",
                    )
                EmptyResponse.model_validate(payload_data)
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
            wait=_wait_with_retry_after_order_groups,
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

                payload_data = response.json() if response.content else {}
                if not isinstance(payload_data, dict):
                    raise KalshiAPIError(
                        response.status_code,
                        "Unexpected delete order group response shape (expected object).",
                    )
                EmptyResponse.model_validate(payload_data)
                return None

        raise AssertionError("AsyncRetrying should have returned or raised")  # pragma: no cover
