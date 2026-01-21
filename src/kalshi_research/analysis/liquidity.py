"""Liquidity analysis for Kalshi markets.

Kalshi orderbooks expose bids on both sides:
- YES bids are actual YES bids.
- NO bids imply YES asks at (100 - no_bid_price).

This module provides:
- Depth scoring (distance-weighted around midpoint)
- Slippage estimation via "walk the book"
- Max safe order size under a slippage constraint
- A composite 0-100 liquidity score
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from kalshi_research.analysis._depth import orderbook_depth_score
from kalshi_research.analysis._liquidity_models import (
    DepthAnalysis,
    ExecutionWindow,
    LiquidityAnalysis,
    LiquidityError,
    LiquidityGrade,
    LiquidityWeights,
    SlippageEstimate,
)
from kalshi_research.analysis._scoring import (
    estimate_price_impact,
    liquidity_score,
    suggest_execution_timing,
)
from kalshi_research.analysis._slippage import (
    enforce_max_slippage,
    estimate_slippage,
    max_safe_order_size,
)
from kalshi_research.constants import DEFAULT_DEPTH_RADIUS_CENTS

if TYPE_CHECKING:
    from kalshi_research.api.models.market import Market
    from kalshi_research.api.models.orderbook import Orderbook


# Re-export all public API
__all__ = [
    "DepthAnalysis",
    "ExecutionWindow",
    "LiquidityAnalysis",
    "LiquidityError",
    "LiquidityGrade",
    "LiquidityWeights",
    "OrderbookAnalyzer",
    "SlippageEstimate",
    "enforce_max_slippage",
    "estimate_price_impact",
    "estimate_slippage",
    "liquidity_score",
    "max_safe_order_size",
    "orderbook_depth_score",
    "suggest_execution_timing",
]


class OrderbookAnalyzer:
    """Convenience wrapper for computing liquidity metrics from an orderbook snapshot."""

    def __init__(
        self,
        *,
        radius_cents: int = DEFAULT_DEPTH_RADIUS_CENTS,
        weights: LiquidityWeights | None = None,
    ) -> None:
        self._radius_cents = radius_cents
        self._weights = weights

    def depth(self, orderbook: Orderbook) -> DepthAnalysis:
        """Compute distance-weighted depth around the midpoint."""
        return orderbook_depth_score(orderbook, radius_cents=self._radius_cents)

    def slippage(
        self,
        orderbook: Orderbook,
        side: Literal["yes", "no"],
        action: Literal["buy", "sell"],
        *,
        quantity: int,
    ) -> SlippageEstimate:
        """Estimate slippage for a hypothetical execution by walking the book."""
        return estimate_slippage(orderbook, side, action, quantity)

    def liquidity(self, market: Market, orderbook: Orderbook) -> LiquidityAnalysis:
        """Compute a composite liquidity analysis for a market and orderbook snapshot."""
        return liquidity_score(market, orderbook, weights=self._weights)
