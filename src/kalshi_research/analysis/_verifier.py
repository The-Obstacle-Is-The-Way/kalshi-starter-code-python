"""Market status verification."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from kalshi_research.api.models.market import Market

from kalshi_research.analysis._scanner_models import MarketClosedError
from kalshi_research.api.models.market import MarketStatus


class MarketStatusVerifier:
    """
    Centralized market timing and status verification.

    Checks if markets are:
    - Still open for trading (not closed)
    - Active (not settled, finalized, etc.)
    - Valid for current operations
    """

    def __init__(self, *, exchange_status: Mapping[str, object] | None = None) -> None:
        self._exchange_status = exchange_status

    def _is_exchange_tradeable(self) -> bool:
        if self._exchange_status is None:
            return True

        exchange_active = self._exchange_status.get("exchange_active")
        trading_active = self._exchange_status.get("trading_active")

        if not isinstance(exchange_active, bool) or not isinstance(trading_active, bool):
            return False

        return exchange_active and trading_active

    def is_market_tradeable(self, market: Market) -> bool:
        """
        Check if a market is currently tradeable.

        A market is tradeable if:
        1. Status is 'active'
        2. Current time < close_time

        Args:
            market: Market to check

        Returns:
            True if market is tradeable, False otherwise
        """
        if not self._is_exchange_tradeable():
            return False

        now = datetime.now(UTC)

        # Check status
        if market.status != MarketStatus.ACTIVE:
            return False

        # Check timing - market must not be past close_time
        return now < market.close_time

    def verify_market_open(self, market: Market) -> None:
        """
        Verify market is open for trading, raise if not.

        Args:
            market: Market to verify

        Raises:
            MarketClosedError: If market is closed or not tradeable
        """
        if not self._is_exchange_tradeable():
            exchange_active = (
                self._exchange_status.get("exchange_active")
                if self._exchange_status is not None
                else None
            )
            trading_active = (
                self._exchange_status.get("trading_active")
                if self._exchange_status is not None
                else None
            )
            raise MarketClosedError(
                "Exchange trading is currently halted "
                f"(exchange_active={exchange_active}, trading_active={trading_active})"
            )

        if not self.is_market_tradeable(market):
            now = datetime.now(UTC)
            if market.status != MarketStatus.ACTIVE:
                raise MarketClosedError(
                    f"Market {market.ticker} has status {market.status.value}, "
                    f"expected {MarketStatus.ACTIVE.value}"
                )
            if now >= market.close_time:
                raise MarketClosedError(
                    f"Market {market.ticker} closed at {market.close_time.isoformat()}, "
                    f"current time is {now.isoformat()}"
                )

    def filter_tradeable_markets(self, markets: list[Market]) -> list[Market]:
        """
        Filter a list of markets to only tradeable ones.

        Args:
            markets: List of markets to filter

        Returns:
            List of tradeable markets
        """
        return [m for m in markets if self.is_market_tradeable(m)]
