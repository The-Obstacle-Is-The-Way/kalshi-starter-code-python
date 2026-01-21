"""FIFO (First-In-First-Out) P&L calculation logic.

This module handles trade normalization and FIFO lot matching for realized P&L
calculation.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from kalshi_research.portfolio._pnl_models import EffectiveTrade, FifoResult, Lot

if TYPE_CHECKING:
    from kalshi_research.portfolio.models import Trade


def normalize_trade_for_fifo(trade: Trade) -> EffectiveTrade:
    """
    Normalize fills into a consistent (ticker, side) stream for FIFO.

    Kalshi's fills are "literal side" and can represent closing trades on the opposite side.
    In practice, this codebase observes that:
    - BUY trades open/increase the literal `trade.side` at `trade.price_cents`.
    - SELL trades close/decrease the *opposite* side at the *inverted* price.

    Example:
    - BUY YES at 51 is stored as (side=yes, action=buy, price=51)
    - Closing that position may appear as (side=no, action=sell, price=88), which is
      economically a SELL YES at (100 - 88) = 12.

    Args:
        trade: The raw trade from Kalshi API.

    Returns:
        Normalized trade representation for FIFO processing.

    Raises:
        ValueError: If trade side, action, or price is invalid.
    """
    side = trade.side.lower()
    if side not in {"yes", "no"}:
        raise ValueError(f"Trade side must be 'yes' or 'no' (got {trade.side!r})")

    action = trade.action.lower()
    if action not in {"buy", "sell"}:
        raise ValueError(f"Trade action must be 'buy' or 'sell' (got {trade.action!r})")

    if trade.price_cents < 0 or trade.price_cents > 100:
        raise ValueError(f"Trade price_cents must be in [0, 100] (got {trade.price_cents})")

    if action == "buy":
        effective_side = side
        effective_price_cents = trade.price_cents
    else:
        effective_side = "no" if side == "yes" else "yes"
        effective_price_cents = 100 - trade.price_cents

    return EffectiveTrade(
        ticker=trade.ticker,
        side=effective_side,
        action=action,
        quantity=trade.quantity,
        price_cents=effective_price_cents,
        total_cost_cents=effective_price_cents * trade.quantity,
        fee_cents=trade.fee_cents,
        executed_at=trade.executed_at,
    )


def get_closed_trade_pnls_fifo(trades: list[Trade]) -> FifoResult:
    """
    Compute per-sell realized P&L in cents using FIFO lots (integer arithmetic).

    Trades are normalized (to handle Kalshi cross-side closing), then grouped by (ticker, side)
    and processed in executed_at order.

    Normalization rules:
    - BUY trades affect the literal side at the literal price.
    - SELL trades affect the opposite side at the inverted price (100 - price).

    This prevents "orphan sells" when a position opened on YES is closed via a NO sell (and
    vice versa), which is observed in real fill history.

    Fees are handled as:
    - Buy fees are included in cost basis by storing lot-level total cost (price * qty + fee).
    - Sell fees reduce proceeds directly.

    Args:
        trades: List of trades to process.

    Returns:
        FifoResult with per-sell P&L values, orphan sell quantity, and remaining open lots.
    """
    ticker_side_trades: dict[tuple[str, str], list[EffectiveTrade]] = {}
    for raw_trade in trades:
        effective_trade = normalize_trade_for_fifo(raw_trade)
        key = (effective_trade.ticker, effective_trade.side)
        ticker_side_trades.setdefault(key, []).append(effective_trade)

    closed_pnls: list[int] = []
    orphan_sell_qty_skipped = 0

    open_lots: dict[tuple[str, str], Lot] = {}

    for key, group_trades in ticker_side_trades.items():
        sorted_trades = sorted(group_trades, key=lambda t: t.executed_at)
        lots: deque[Lot] = deque()

        for trade in sorted_trades:
            if trade.quantity <= 0:
                raise ValueError("Trade quantity must be positive")

            if trade.action == "buy":
                lots.append(
                    Lot(
                        qty_remaining=trade.quantity,
                        cost_remaining_cents=trade.total_cost_cents + trade.fee_cents,
                    )
                )
                continue

            if trade.action == "sell":
                remaining_to_sell = trade.quantity
                matched_qty = 0
                cost_basis_cents = 0

                while remaining_to_sell > 0:
                    if not lots:
                        orphan_sell_qty_skipped += remaining_to_sell
                        break

                    lot = lots[0]
                    consume_qty = min(lot.qty_remaining, remaining_to_sell)
                    matched_qty += consume_qty
                    # Use round() to avoid systematic downward bias from floor division
                    # This matches the pattern in syncer.py:compute_fifo_cost_basis
                    consume_cost_cents = round(
                        lot.cost_remaining_cents * consume_qty / lot.qty_remaining
                    )
                    cost_basis_cents += consume_cost_cents

                    lot.cost_remaining_cents -= consume_cost_cents
                    lot.qty_remaining -= consume_qty
                    remaining_to_sell -= consume_qty

                    if lot.qty_remaining == 0:
                        lots.popleft()

                if matched_qty == 0:
                    continue

                # Only count proceeds for the portion we could match against FIFO lots.
                # Fee is prorated to the matched quantity.
                matched_fee_cents = round(trade.fee_cents * matched_qty / trade.quantity)
                net_proceeds_cents = (trade.price_cents * matched_qty) - matched_fee_cents
                closed_pnls.append(net_proceeds_cents - cost_basis_cents)
                continue

        if not lots:
            continue

        qty_remaining = sum(lot.qty_remaining for lot in lots)
        cost_remaining = sum(lot.cost_remaining_cents for lot in lots)
        if qty_remaining <= 0:
            continue

        open_lots[key] = Lot(qty_remaining=qty_remaining, cost_remaining_cents=cost_remaining)

    return FifoResult(
        closed_pnls=closed_pnls,
        orphan_sell_qty_skipped=orphan_sell_qty_skipped,
        open_lots=open_lots,
    )
