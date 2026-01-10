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

import math
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from decimal import Decimal

    from kalshi_research.api.models.market import Market
    from kalshi_research.api.models.orderbook import Orderbook


class LiquidityGrade(str, Enum):
    """Liquidity grade classification."""

    ILLIQUID = "illiquid"
    THIN = "thin"
    MODERATE = "moderate"
    LIQUID = "liquid"


class LiquidityError(RuntimeError):
    """Raised when a proposed execution exceeds liquidity constraints."""


@dataclass(frozen=True)
class DepthAnalysis:
    """Orderbook depth analysis results."""

    total_contracts: int
    weighted_score: float
    yes_side_depth: int
    no_side_depth: int
    imbalance_ratio: float


def orderbook_depth_score(orderbook: Orderbook, *, radius_cents: int = 10) -> DepthAnalysis:
    """Calculate a distance-weighted depth score around the YES midpoint.

    Notes:
        - YES bids are already in YES-price terms.
        - NO bids imply YES asks at (100 - no_bid_price). We convert NO bids to implied YES asks
          for distance calculations so both sides are comparable around the same midpoint.
    """
    if radius_cents < 0:
        raise ValueError("radius_cents must be >= 0")

    midpoint: Decimal | None = orderbook.midpoint
    if midpoint is None:
        return DepthAnalysis(0, 0.0, 0, 0, 0.0)

    midpoint_float = float(midpoint)
    weighted_score = 0.0
    yes_depth = 0
    no_depth = 0

    # YES side: bids in YES cents
    for price, qty in orderbook.yes_levels:
        distance = abs(price - midpoint_float)
        if distance <= radius_cents:
            weight = 1.0 if radius_cents == 0 else 1.0 - (distance / (radius_cents + 1))
            weighted_score += qty * weight
            yes_depth += qty

    # NO side: bids in NO cents, convert to implied YES asks for distance-from-midpoint comparisons
    for no_price, qty in orderbook.no_levels:
        implied_yes_ask = 100 - no_price
        distance = abs(implied_yes_ask - midpoint_float)
        if distance <= radius_cents:
            weight = 1.0 if radius_cents == 0 else 1.0 - (distance / (radius_cents + 1))
            weighted_score += qty * weight
            no_depth += qty

    total = yes_depth + no_depth
    imbalance = (yes_depth - no_depth) / max(total, 1)

    return DepthAnalysis(
        total_contracts=total,
        weighted_score=weighted_score,
        yes_side_depth=yes_depth,
        no_side_depth=no_depth,
        imbalance_ratio=imbalance,
    )


@dataclass(frozen=True)
class SlippageEstimate:
    """Slippage estimation results for a hypothetical execution."""

    best_price: int
    avg_fill_price: float
    worst_price: int
    slippage_cents: float
    slippage_pct: float
    fillable_quantity: int
    remaining_unfilled: int
    levels_crossed: int


def _invert_levels(levels: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Convert bid levels to implied ask levels (100 - price)."""
    return [(100 - price, qty) for price, qty in levels]


def _levels_for_execution(
    orderbook: Orderbook,
    side: Literal["yes", "no"],
    action: Literal["buy", "sell"],
) -> list[tuple[int, int]]:
    """Return executable levels (price, qty) for an action, in the correct price domain."""
    if side == "yes":
        if action == "buy":
            # Buy YES = cross implied YES asks (from NO bids)
            levels = _invert_levels(orderbook.no_levels)
            return sorted(levels, key=lambda x: x[0])  # lowest ask first
        # Sell YES = hit YES bids
        return sorted(orderbook.yes_levels, key=lambda x: x[0], reverse=True)  # highest bid first

    if action == "buy":
        # Buy NO = cross implied NO asks (from YES bids)
        levels = _invert_levels(orderbook.yes_levels)
        return sorted(levels, key=lambda x: x[0])  # lowest ask first
    # Sell NO = hit NO bids
    return sorted(orderbook.no_levels, key=lambda x: x[0], reverse=True)  # highest bid first


def estimate_slippage(
    orderbook: Orderbook,
    side: Literal["yes", "no"],
    action: Literal["buy", "sell"],
    quantity: int,
) -> SlippageEstimate:
    """Estimate execution price for a given order size by walking the book."""
    if quantity <= 0:
        raise ValueError("quantity must be > 0")

    levels = _levels_for_execution(orderbook, side, action)
    if not levels:
        return SlippageEstimate(
            best_price=0,
            avg_fill_price=0.0,
            worst_price=0,
            slippage_cents=0.0,
            slippage_pct=0.0,
            fillable_quantity=0,
            remaining_unfilled=quantity,
            levels_crossed=0,
        )

    best_price = levels[0][0]
    filled = 0
    cost = 0.0
    levels_crossed = 0
    worst_price = best_price

    for price, available_qty in levels:
        if filled >= quantity:
            break
        take = min(available_qty, quantity - filled)
        if take <= 0:
            continue
        filled += take
        cost += take * price
        worst_price = price
        levels_crossed += 1

    avg_fill = cost / filled if filled > 0 else 0.0
    slippage = avg_fill - best_price if action == "buy" else best_price - avg_fill

    slippage_cents = max(0.0, float(slippage))
    slippage_pct = (slippage_cents / best_price * 100) if best_price > 0 else 0.0

    return SlippageEstimate(
        best_price=best_price,
        avg_fill_price=avg_fill,
        worst_price=worst_price,
        slippage_cents=slippage_cents,
        slippage_pct=slippage_pct,
        fillable_quantity=filled,
        remaining_unfilled=quantity - filled,
        levels_crossed=levels_crossed,
    )


def enforce_max_slippage(
    orderbook: Orderbook,
    side: Literal["yes", "no"],
    action: Literal["buy", "sell"],
    *,
    quantity: int,
    max_slippage_pct: float,
) -> SlippageEstimate:
    """Validate a proposed execution against a max slippage constraint.

    Raises:
        LiquidityError: If the order is not fully fillable or exceeds the slippage limit.
    """
    if max_slippage_pct < 0:
        raise ValueError("max_slippage_pct must be >= 0")

    estimate = estimate_slippage(orderbook, side, action, quantity)
    if estimate.remaining_unfilled > 0:
        raise LiquidityError(
            f"Insufficient depth: requested {quantity}, fillable {estimate.fillable_quantity}."
        )

    if estimate.slippage_pct > max_slippage_pct:
        raise LiquidityError(
            f"Order would incur {estimate.slippage_pct:.1f}% slippage "
            f"(max allowed {max_slippage_pct:.1f}%)."
        )

    return estimate


def max_safe_order_size(
    orderbook: Orderbook,
    side: Literal["yes", "no"],
    *,
    max_slippage_cents: int = 3,
) -> int:
    """Calculate largest BUY order within a slippage tolerance."""
    if max_slippage_cents < 0:
        raise ValueError("max_slippage_cents must be >= 0")

    # Maximum fillable size is the sum of executable ask-side quantities for a BUY.
    ask_levels = _levels_for_execution(orderbook, side, "buy")
    max_possible = sum(qty for _, qty in ask_levels)
    if max_possible <= 0:
        return 0

    low, high = 1, max_possible
    best = 0

    while low <= high:
        mid = (low + high) // 2
        estimate = estimate_slippage(orderbook, side, "buy", mid)

        # Treat unfillable sizes as unsafe.
        if estimate.remaining_unfilled > 0:
            high = mid - 1
            continue

        if estimate.slippage_cents <= max_slippage_cents:
            best = mid
            low = mid + 1
        else:
            high = mid - 1

    return best


def estimate_price_impact(
    market: Market,
    orderbook: Orderbook,
    *,
    order_quantity: int,
    impact_factor: float = 0.1,
) -> float:
    """Estimate market price impact (cents) using a square-root style model."""
    if order_quantity <= 0:
        raise ValueError("order_quantity must be > 0")
    if impact_factor < 0:
        raise ValueError("impact_factor must be >= 0")

    spread = orderbook.spread if orderbook.spread is not None else 10
    adtv = max(market.volume_24h, 1)
    sqrt_component = impact_factor * math.sqrt(order_quantity / adtv)
    impact_cents = (spread / 2) + (sqrt_component * 100)
    return min(float(impact_cents), 50.0)


@dataclass(frozen=True)
class LiquidityWeights:
    """Weights for composite liquidity score."""

    spread: float = 0.30
    depth: float = 0.30
    volume: float = 0.20
    open_interest: float = 0.20

    def __post_init__(self) -> None:
        total = self.spread + self.depth + self.volume + self.open_interest
        if abs(total - 1.0) >= 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


@dataclass(frozen=True)
class LiquidityAnalysis:
    """Composite liquidity analysis for a market."""

    score: int
    grade: LiquidityGrade
    components: dict[str, float]
    depth: DepthAnalysis
    max_safe_size_yes: int
    max_safe_size_no: int
    warnings: list[str]


def _spread_score(spread_cents: int) -> float:
    """Map spread (cents) to a 0-100 score (1c->100, 20c+->0)."""
    if spread_cents <= 1:
        return 100.0
    if spread_cents >= 20:
        return 0.0
    # Linear interpolation from (1,100) to (20,0)
    return max(0.0, 100.0 - ((spread_cents - 1) * (100.0 / 19.0)))


def liquidity_score(
    market: Market,
    orderbook: Orderbook,
    *,
    weights: LiquidityWeights | None = None,
) -> LiquidityAnalysis:
    """Compute a composite 0-100 liquidity score with an interpretable grade."""
    w = weights or LiquidityWeights()
    warnings: list[str] = []

    spread = orderbook.spread if orderbook.spread is not None else 100
    spread_score = _spread_score(spread)
    if spread > 10:
        warnings.append(f"Wide spread ({spread}c) will eat edge")

    depth = orderbook_depth_score(orderbook, radius_cents=10)
    depth_score = min(100.0, depth.weighted_score / 10.0)
    if depth.total_contracts < 100:
        warnings.append(f"Thin book ({depth.total_contracts} contracts near mid)")

    if abs(depth.imbalance_ratio) > 0.5:
        side = "YES" if depth.imbalance_ratio > 0 else "NO"
        warnings.append(f"Orderbook imbalance: {side} side has more near-mid depth")

    volume_score = min(100.0, market.volume_24h / 100.0)
    if market.volume_24h < 1000:
        warnings.append(f"Low volume ({market.volume_24h}/24h)")

    oi_score = min(100.0, market.open_interest / 50.0)

    score_float = (
        spread_score * w.spread
        + depth_score * w.depth
        + volume_score * w.volume
        + oi_score * w.open_interest
    )
    score = int(max(0.0, min(100.0, score_float)))

    if score >= 76:
        grade = LiquidityGrade.LIQUID
    elif score >= 51:
        grade = LiquidityGrade.MODERATE
    elif score >= 26:
        grade = LiquidityGrade.THIN
    else:
        grade = LiquidityGrade.ILLIQUID
        warnings.append("ILLIQUID: consider skipping or sizing down significantly")

    max_yes = max_safe_order_size(orderbook, "yes", max_slippage_cents=3)
    max_no = max_safe_order_size(orderbook, "no", max_slippage_cents=3)

    return LiquidityAnalysis(
        score=score,
        grade=grade,
        components={
            "spread": spread_score,
            "depth": depth_score,
            "volume": volume_score,
            "open_interest": oi_score,
        },
        depth=depth,
        max_safe_size_yes=max_yes,
        max_safe_size_no=max_no,
        warnings=warnings,
    )


@dataclass(frozen=True)
class ExecutionWindow:
    """Recommended execution timing (heuristic)."""

    optimal_hours_utc: list[int]
    avoid_hours_utc: list[int]
    reasoning: str


def suggest_execution_timing() -> ExecutionWindow:
    """Suggest execution timing based on typical US-hours liquidity patterns."""
    optimal = list(range(13, 22))  # 13:00-21:00 UTC = 9am-5pm ET
    avoid = list(range(0, 12))  # Overnight UTC
    return ExecutionWindow(
        optimal_hours_utc=optimal,
        avoid_hours_utc=avoid,
        reasoning="Liquidity often peaks during US market hours (9am-5pm ET).",
    )


class OrderbookAnalyzer:
    """Convenience wrapper for computing liquidity metrics from an orderbook snapshot."""

    def __init__(
        self,
        *,
        radius_cents: int = 10,
        weights: LiquidityWeights | None = None,
    ) -> None:
        self._radius_cents = radius_cents
        self._weights = weights

    def depth(self, orderbook: Orderbook) -> DepthAnalysis:
        return orderbook_depth_score(orderbook, radius_cents=self._radius_cents)

    def slippage(
        self,
        orderbook: Orderbook,
        side: Literal["yes", "no"],
        action: Literal["buy", "sell"],
        *,
        quantity: int,
    ) -> SlippageEstimate:
        return estimate_slippage(orderbook, side, action, quantity)

    def max_safe_buy_size(
        self,
        orderbook: Orderbook,
        side: Literal["yes", "no"],
        *,
        max_slippage_cents: int = 3,
    ) -> int:
        return max_safe_order_size(orderbook, side, max_slippage_cents=max_slippage_cents)

    def liquidity(self, market: Market, orderbook: Orderbook) -> LiquidityAnalysis:
        return liquidity_score(market, orderbook, weights=self._weights)
