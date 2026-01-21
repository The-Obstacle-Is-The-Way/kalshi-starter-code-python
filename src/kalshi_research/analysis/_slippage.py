"""Slippage estimation and execution constraint enforcement.

Provides:
- Slippage estimation by "walking the book"
- Max slippage enforcement
- Max safe order size calculation
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from kalshi_research.analysis._liquidity_models import LiquidityError, SlippageEstimate
from kalshi_research.constants import DEFAULT_MAX_SLIPPAGE_CENTS

if TYPE_CHECKING:
    from kalshi_research.api.models.orderbook import Orderbook


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
    max_slippage_cents: int = DEFAULT_MAX_SLIPPAGE_CENTS,
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
