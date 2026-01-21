"""Helper functions and data classes for portfolio synchronization."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kalshi_research.portfolio.models import Trade


def compute_fifo_cost_basis(trades: list[Trade], side: str) -> int:
    """
    Compute average cost basis for a position using FIFO.

    FIFO (First-In-First-Out) is the IRS default method and the safest choice.
    We track a queue of lots and compute weighted average of remaining shares.

    Args:
        trades: List of Trade records for this ticker, sorted by executed_at
        side: "yes" or "no" - the position side we're computing cost for

    Returns:
        Average cost basis in cents (0 if no position)

    Reference: https://coinledger.io/blog/cryptocurrency-tax-calculations-fifo-and-lifo-costing-methods-explained
    """
    # Queue of lots: (quantity, price_cents)
    lots: deque[tuple[int, int]] = deque()

    for trade in trades:
        # Filter to trades matching the position side
        if trade.side != side:
            continue

        price = trade.price_cents
        qty = trade.quantity

        if trade.action == "buy":
            # Add to position - push lot onto queue
            lots.append((qty, price))
        elif trade.action == "sell":
            # Reduce position - pop FIFO from queue
            remaining = qty
            while remaining > 0 and lots:
                lot_qty, _lot_price = lots[0]
                if lot_qty <= remaining:
                    # Consume entire lot
                    lots.popleft()
                    remaining -= lot_qty
                else:
                    # Partial lot consumption
                    lots[0] = (lot_qty - remaining, _lot_price)
                    remaining = 0

    # Compute weighted average of remaining lots
    if not lots:
        return 0

    total_qty = sum(qty for qty, _ in lots)
    total_cost = sum(qty * price for qty, price in lots)

    if total_qty == 0:
        return 0

    # Use standard division and round to nearest cent
    # This avoids precision loss from floor division (//)
    # Example: 101/2 = 50.5 -> rounds to 50 or 51 depending on rounding
    # Using round() for standard half-to-even rounding (banker's rounding)
    return round(total_cost / total_qty)


@dataclass
class SyncResult:
    """Result of a portfolio sync operation."""

    positions_synced: int
    trades_synced: int
    settlements_synced: int = 0
    errors: list[str] | None = None
