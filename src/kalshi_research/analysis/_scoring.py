"""Composite liquidity scoring and execution timing heuristics.

Provides:
- Price impact estimation
- Composite liquidity score calculation
- Execution timing suggestions
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from kalshi_research.analysis._depth import orderbook_depth_score
from kalshi_research.analysis._liquidity_models import (
    ExecutionWindow,
    LiquidityAnalysis,
    LiquidityGrade,
    LiquidityWeights,
)
from kalshi_research.analysis._slippage import max_safe_order_size
from kalshi_research.constants import (
    DEFAULT_DEPTH_RADIUS_CENTS,
    DEFAULT_MAX_SLIPPAGE_CENTS,
    LIQUIDITY_GRADE_LIQUID_THRESHOLD,
    LIQUIDITY_GRADE_MODERATE_THRESHOLD,
    LIQUIDITY_GRADE_THIN_THRESHOLD,
    LIQUIDITY_WARNING_DEPTH_CONTRACTS,
    LIQUIDITY_WARNING_IMBALANCE_RATIO,
    LIQUIDITY_WARNING_SPREAD_CENTS,
    LIQUIDITY_WARNING_VOLUME_24H,
    SPREAD_SCORE_BEST_CENTS,
    SPREAD_SCORE_WORST_CENTS,
)

if TYPE_CHECKING:
    from kalshi_research.api.models.market import Market
    from kalshi_research.api.models.orderbook import Orderbook


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


def _spread_score(spread_cents: int) -> float:
    """Map spread (cents) to a 0-100 score (1c->100, 20c+->0)."""
    if spread_cents <= SPREAD_SCORE_BEST_CENTS:
        return 100.0
    if spread_cents >= SPREAD_SCORE_WORST_CENTS:
        return 0.0
    # Linear interpolation from (best,100) to (worst,0)
    interpolation_range = SPREAD_SCORE_WORST_CENTS - SPREAD_SCORE_BEST_CENTS
    return max(
        0.0, 100.0 - ((spread_cents - SPREAD_SCORE_BEST_CENTS) * (100.0 / interpolation_range))
    )


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
    spread_sc = _spread_score(spread)
    if spread > LIQUIDITY_WARNING_SPREAD_CENTS:
        warnings.append(f"Wide spread ({spread}c) will eat edge")

    depth = orderbook_depth_score(orderbook, radius_cents=DEFAULT_DEPTH_RADIUS_CENTS)
    depth_score = min(100.0, depth.weighted_score / 10.0)
    if depth.total_contracts < LIQUIDITY_WARNING_DEPTH_CONTRACTS:
        warnings.append(f"Thin book ({depth.total_contracts} contracts near mid)")

    if abs(depth.imbalance_ratio) > LIQUIDITY_WARNING_IMBALANCE_RATIO:
        side = "YES" if depth.imbalance_ratio > 0 else "NO"
        warnings.append(f"Orderbook imbalance: {side} side has more near-mid depth")

    volume_score = min(100.0, market.volume_24h / 100.0)
    if market.volume_24h < LIQUIDITY_WARNING_VOLUME_24H:
        warnings.append(f"Low volume ({market.volume_24h}/24h)")

    oi_score = min(100.0, market.open_interest / 50.0)

    score_float = (
        spread_sc * w.spread
        + depth_score * w.depth
        + volume_score * w.volume
        + oi_score * w.open_interest
    )
    score = int(max(0.0, min(100.0, score_float)))

    if score >= LIQUIDITY_GRADE_LIQUID_THRESHOLD:
        grade = LiquidityGrade.LIQUID
    elif score >= LIQUIDITY_GRADE_MODERATE_THRESHOLD:
        grade = LiquidityGrade.MODERATE
    elif score >= LIQUIDITY_GRADE_THIN_THRESHOLD:
        grade = LiquidityGrade.THIN
    else:
        grade = LiquidityGrade.ILLIQUID
        warnings.append("ILLIQUID: consider skipping or sizing down significantly")

    max_yes = max_safe_order_size(orderbook, "yes", max_slippage_cents=DEFAULT_MAX_SLIPPAGE_CENTS)
    max_no = max_safe_order_size(orderbook, "no", max_slippage_cents=DEFAULT_MAX_SLIPPAGE_CENTS)

    return LiquidityAnalysis(
        score=score,
        grade=grade,
        components={
            "spread": spread_sc,
            "depth": depth_score,
            "volume": volume_score,
            "open_interest": oi_score,
        },
        depth=depth,
        max_safe_size_yes=max_yes,
        max_safe_size_no=max_no,
        warnings=warnings,
    )


def suggest_execution_timing() -> ExecutionWindow:
    """Suggest execution timing based on typical US-hours liquidity patterns."""
    optimal = list(range(13, 22))  # 13:00-21:00 UTC = 9am-5pm ET
    avoid = list(range(0, 12))  # Overnight UTC
    return ExecutionWindow(
        optimal_hours_utc=optimal,
        avoid_hours_utc=avoid,
        reasoning="Liquidity often peaks during US market hours (9am-5pm ET).",
    )
