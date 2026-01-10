"""P&L (Profit and Loss) calculator for portfolio positions."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kalshi_research.portfolio.models import Position, Trade


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


class PnLCalculator:
    """Calculate profit/loss on positions and trades."""

    @dataclass
    class _Lot:
        qty_remaining: int
        cost_remaining_cents: int

    def calculate_unrealized(self, position: Position, current_price_cents: int) -> int:
        """
        Calculate unrealized P&L for a position in cents.

        For YES positions: (current_price - avg_price) * quantity
        For NO positions: (avg_price - current_price) * quantity
        """
        if position.side == "yes":
            return (current_price_cents - position.avg_price_cents) * position.quantity
        else:
            return (position.avg_price_cents - current_price_cents) * position.quantity

    def _get_closed_trade_pnls_fifo(self, trades: list[Trade]) -> list[int]:
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
                    cost_basis_cents = 0

                    while remaining_to_sell > 0:
                        if not lots:
                            raise ValueError(
                                "Sell trade exceeds available FIFO lots; trade history is "
                                "incomplete"
                            )

                        lot = lots[0]
                        consume_qty = min(lot.qty_remaining, remaining_to_sell)
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

                    net_proceeds_cents = trade.total_cost_cents - trade.fee_cents
                    closed_pnls.append(net_proceeds_cents - cost_basis_cents)
                    continue

        return closed_pnls

    def calculate_realized(self, trades: list[Trade]) -> int:
        """
        Calculate realized P&L from a list of trades.

        Realized P&L is calculated from closed positions (matched buy/sell pairs).
        Groups by (ticker, side) to handle YES/NO positions separately.
        """
        return sum(self._get_closed_trade_pnls_fifo(trades))

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
        self, positions: list[Position], trades: list[Trade]
    ) -> PnLSummary:
        """Calculate complete P&L summary including trade statistics."""
        unrealized_positions_unknown = sum(
            1 for pos in positions if pos.unrealized_pnl_cents is None
        )
        unrealized = sum(
            pos.unrealized_pnl_cents for pos in positions if pos.unrealized_pnl_cents is not None
        )
        closed_trades = self._get_closed_trade_pnls_fifo(trades)
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
        return self._get_closed_trade_pnls_fifo(trades)
