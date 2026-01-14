"""P&L (Profit and Loss) calculator for portfolio positions."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from kalshi_research.portfolio.models import PortfolioSettlement, Position, Trade


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


class PnLCalculator:
    """Calculate profit/loss on positions and trades."""

    @dataclass
    class _Lot:
        qty_remaining: int
        cost_remaining_cents: int

    @dataclass(frozen=True)
    class _EffectiveTrade:
        ticker: str
        side: str
        action: str
        quantity: int
        price_cents: int
        total_cost_cents: int
        fee_cents: int
        executed_at: datetime

    @dataclass
    class _FifoResult:
        closed_pnls: list[int]
        orphan_sell_qty_skipped: int

    @staticmethod
    def _normalize_trade_for_fifo(trade: Trade) -> _EffectiveTrade:
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

        return PnLCalculator._EffectiveTrade(
            ticker=trade.ticker,
            side=effective_side,
            action=action,
            quantity=trade.quantity,
            price_cents=effective_price_cents,
            total_cost_cents=effective_price_cents * trade.quantity,
            fee_cents=trade.fee_cents,
            executed_at=trade.executed_at,
        )

    def calculate_unrealized(self, position: Position, current_price_cents: int) -> int:
        """
        Calculate unrealized P&L for a position in cents.

        Prices in this codebase are stored in contract cents for the position side (YES or NO).
        Unrealized P&L is therefore always:

            (current_price - avg_price) * quantity
        """
        return (current_price_cents - position.avg_price_cents) * position.quantity

    def _get_closed_trade_pnls_fifo(self, trades: list[Trade]) -> _FifoResult:
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
        """
        ticker_side_trades: dict[tuple[str, str], list[PnLCalculator._EffectiveTrade]] = {}
        for raw_trade in trades:
            effective_trade = self._normalize_trade_for_fifo(raw_trade)
            key = (effective_trade.ticker, effective_trade.side)
            ticker_side_trades.setdefault(key, []).append(effective_trade)

        closed_pnls: list[int] = []
        orphan_sell_qty_skipped = 0

        for group_trades in ticker_side_trades.values():
            sorted_trades = sorted(group_trades, key=lambda t: t.executed_at)
            lots: deque[PnLCalculator._Lot] = deque()

            for trade in sorted_trades:
                if trade.quantity <= 0:
                    raise ValueError("Trade quantity must be positive")

                if trade.action == "buy":
                    lots.append(
                        PnLCalculator._Lot(
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

        return PnLCalculator._FifoResult(
            closed_pnls=closed_pnls,
            orphan_sell_qty_skipped=orphan_sell_qty_skipped,
        )

    def calculate_realized(self, trades: list[Trade]) -> int:
        """
        Calculate realized P&L from a list of trades.

        Realized P&L is calculated from closed positions (matched buy/sell pairs) using FIFO lots.

        Kalshi fill history can represent closing trades on the opposite side (see vendor doc note
        on "Cross-Side Closing"). This method normalizes trades before matching so that closes are
        correctly attributed and priced.
        """
        return sum(self._get_closed_trade_pnls_fifo(trades).closed_pnls)

    def calculate_total(self, positions: list[Position]) -> PnLSummary:
        """Calculate total P&L summary across all positions."""
        open_positions = [pos for pos in positions if pos.closed_at is None and pos.quantity > 0]
        unrealized_positions_unknown = sum(
            1 for pos in open_positions if pos.unrealized_pnl_cents is None
        )
        unrealized = sum(
            pos.unrealized_pnl_cents
            for pos in open_positions
            if pos.unrealized_pnl_cents is not None
        )
        realized = sum(pos.realized_pnl_cents for pos in positions)
        total = unrealized + realized

        # For now, return basic summary
        # Trade statistics require trade history
        return PnLSummary(
            unrealized_pnl_cents=unrealized,
            realized_pnl_cents=realized,
            total_pnl_cents=total,
            unrealized_positions_unknown=unrealized_positions_unknown,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            avg_win_cents=0,
            avg_loss_cents=0,
            profit_factor=0.0,
        )

    def calculate_summary_with_trades(
        self,
        positions: list[Position],
        trades: list[Trade],
        settlements: list[PortfolioSettlement] | None = None,
    ) -> PnLSummary:
        """Calculate complete P&L summary including trade statistics."""
        open_positions = [pos for pos in positions if pos.closed_at is None and pos.quantity > 0]
        unrealized_positions_unknown = sum(
            1 for pos in open_positions if pos.unrealized_pnl_cents is None
        )
        unrealized = sum(
            pos.unrealized_pnl_cents
            for pos in open_positions
            if pos.unrealized_pnl_cents is not None
        )
        fifo_result = self._get_closed_trade_pnls_fifo(trades)

        settlement_pnls: list[int] = []
        if settlements:
            for settlement in settlements:
                try:
                    fee_cents = int(
                        (Decimal(settlement.fee_cost_dollars) * 100).to_integral_value(
                            rounding=ROUND_HALF_EVEN
                        )
                    )
                except (InvalidOperation, ValueError):
                    fee_cents = 0

                settlement_pnls.append(
                    settlement.revenue
                    - settlement.yes_total_cost
                    - settlement.no_total_cost
                    - fee_cents
                )

        closed_trades = fifo_result.closed_pnls + settlement_pnls

        realized = sum(closed_trades)
        total = unrealized + realized

        winning = [t for t in closed_trades if t > 0]
        losing = [t for t in closed_trades if t < 0]

        total_trades = len(closed_trades)
        winning_trades = len(winning)
        losing_trades = len(losing)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        avg_win = sum(winning) // len(winning) if winning else 0
        avg_loss = abs(sum(losing) // len(losing)) if losing else 0
        profit_factor = abs(sum(winning) / sum(losing)) if losing and sum(losing) != 0 else 0.0

        return PnLSummary(
            unrealized_pnl_cents=unrealized,
            realized_pnl_cents=realized,
            total_pnl_cents=total,
            unrealized_positions_unknown=unrealized_positions_unknown,
            orphan_sell_qty_skipped=fifo_result.orphan_sell_qty_skipped,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_win_cents=avg_win,
            avg_loss_cents=avg_loss,
            profit_factor=profit_factor,
        )

    def _get_closed_trades(self, trades: list[Trade]) -> list[int]:
        """Extract per-sell realized P&L values (FIFO)."""
        return self._get_closed_trade_pnls_fifo(trades).closed_pnls
