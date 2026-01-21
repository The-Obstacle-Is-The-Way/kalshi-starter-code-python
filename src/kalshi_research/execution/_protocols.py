"""Protocol definitions for the trade execution safety harness."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from kalshi_research.api.models.market import Market
    from kalshi_research.api.models.order import OrderSide
    from kalshi_research.api.models.orderbook import Orderbook


class PositionProvider(Protocol):
    """Protocol for querying current position state."""

    async def get_position_quantity(self, ticker: str, side: OrderSide) -> int:
        """Return the current signed position quantity for a ticker+side.

        Returns 0 if no position exists.
        """
        ...


class DailyBudgetTracker(Protocol):
    """Protocol for tracking daily spending and losses."""

    async def get_daily_spend_usd(self) -> float:
        """Return total USD spent today (live orders)."""
        ...

    async def get_daily_loss_usd(self) -> float:
        """Return total realized loss today (positive = loss)."""
        ...


class OrderbookProvider(Protocol):
    """Protocol for fetching orderbook snapshots."""

    async def get_orderbook(self, ticker: str) -> Orderbook:
        """Fetch current orderbook for a market."""
        ...


class MarketProvider(Protocol):
    """Protocol for fetching market data."""

    async def get_market(self, ticker: str) -> Market:
        """Fetch market metadata."""
        ...
