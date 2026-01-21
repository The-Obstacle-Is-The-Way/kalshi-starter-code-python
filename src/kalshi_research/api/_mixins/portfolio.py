"""Portfolio read endpoint mixin (authenticated)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kalshi_research.api.models.portfolio import (
    FillPage,
    GetOrderResponse,
    Order,
    OrderPage,
    PortfolioBalance,
    PortfolioPosition,
    SettlementPage,
)


class PortfolioMixin:
    """Mixin providing portfolio read endpoints (authenticated)."""

    if TYPE_CHECKING:
        # Implemented by KalshiClient
        async def _auth_get(
            self, path: str, params: dict[str, Any] | None = None
        ) -> dict[str, Any]: ...

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
        params: dict[str, Any] = {"limit": max(1, min(limit, 200))}
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
        params: dict[str, Any] = {"limit": max(1, min(limit, 200))}
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

    async def get_order(self, order_id: str) -> Order:
        """Fetch a single order by order ID."""
        data = await self._auth_get(f"/portfolio/orders/{order_id}")
        parsed = GetOrderResponse.model_validate(data)
        return parsed.order
