"""P&L (Profit and Loss) calculator for portfolio positions."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
    orphan_sells_skipped: int = 0


class PnLCalculator:
    """Calculate profit/loss on positions and trades."""

    @dataclass
    class _Lot:
        qty_remaining: int
        cost_remaining_cents: int

    @dataclass
    class _FifoResult:
        closed_pnls: list[int]
        orphan_sells_skipped: int

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

        Trades are grouped by (ticker, side) and processed in executed_at order.
        Fees are handled as:
        - Buy fees are included in cost basis by storing lot-level total cost (price * qty + fee).
        - Sell fees reduce proceeds directly.
        """
        ticker_side_trades: dict[tuple[str, str], list[Trade]] = {}
        for trade in trades:
            key = (trade.ticker, trade.side)
            ticker_side_trades.setdefault(key, []).append(trade)

        closed_pnls: list[int] = []
        orphan_sells_skipped = 0

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
                            orphan_sells_skipped += remaining_to_sell
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
            orphan_sells_skipped=orphan_sells_skipped,
        )

    def calculate_realized(self, trades: list[Trade]) -> int:
        """
        Calculate realized P&L from a list of trades.

        Realized P&L is calculated from closed positions (matched buy/sell pairs).
        Groups by (ticker, side) to handle YES/NO positions separately.
        """
        return sum(self._get_closed_trade_pnls_fifo(trades).closed_pnls)

    def calculate_total(self, positions: list[Position]) -> PnLSummary:
        """Calculate total P&L summary across all positions."""
        unrealized_positions_unknown = sum(
            1 for pos in positions if pos.unrealized_pnl_cents is None
        )
        unrealized = sum(
            pos.unrealized_pnl_cents for pos in positions if pos.unrealized_pnl_cents is not None
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
        unrealized_positions_unknown = sum(
            1 for pos in positions if pos.unrealized_pnl_cents is None
        )
        unrealized = sum(
            pos.unrealized_pnl_cents for pos in positions if pos.unrealized_pnl_cents is not None
        )
        fifo_result = self._get_closed_trade_pnls_fifo(trades)

        settlement_pnls: list[int] = []
        if settlements:
            for settlement in settlements:
                try:
                    fee_cents = int(
                        (Decimal(settlement.fee_cost_dollars) * 100).to_integral_value(
                            rounding=ROUND_HALF_UP
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
            orphan_sells_skipped=fifo_result.orphan_sells_skipped,
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
