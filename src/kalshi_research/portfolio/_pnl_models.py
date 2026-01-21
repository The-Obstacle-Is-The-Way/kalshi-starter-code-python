"""P&L data models for portfolio analysis.

These dataclasses are used internally by the P&L calculator and represent:
- Summary output (PnLSummary)
- FIFO lot tracking (Lot)
- Normalized trade representation (EffectiveTrade)
- FIFO calculation results (FifoResult)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class PnLSummary:
    """Summary of portfolio profit and loss."""

    unrealized_pnl_cents: int
    realized_pnl_cents: int
    total_pnl_cents: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win_cents: int
    avg_loss_cents: int
    profit_factor: float
    unrealized_positions_unknown: int = 0
    orphan_sell_qty_skipped: int = 0


@dataclass
class Lot:
    """FIFO lot for tracking cost basis.

    Represents a portion of a position that was acquired at a specific cost.
    """

    qty_remaining: int
    cost_remaining_cents: int


@dataclass(frozen=True)
class EffectiveTrade:
    """Normalized trade representation for FIFO processing.

    Kalshi trades are "literal side" and can represent closing trades on the
    opposite side. This dataclass represents the effective trade after
    normalization.

    Normalization rules:
    - BUY trades affect the literal side at the literal price.
    - SELL trades affect the opposite side at the inverted price (100 - price).
    """

    ticker: str
    side: str
    action: str
    quantity: int
    price_cents: int
    total_cost_cents: int
    fee_cents: int
    executed_at: datetime


@dataclass
class FifoResult:
    """Result of FIFO P&L calculation.

    Contains per-sell P&L values, orphan sell quantity, and remaining open lots.
    """

    closed_pnls: list[int]
    orphan_sell_qty_skipped: int
    open_lots: dict[tuple[str, str], Lot]
