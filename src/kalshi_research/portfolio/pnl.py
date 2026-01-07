"""P&L (Profit and Loss) calculator for portfolio positions."""

from __future__ import annotations

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


class PnLCalculator:
    """Calculate profit/loss on positions and trades."""

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

    def calculate_realized(self, trades: list[Trade]) -> int:
        """
        Calculate realized P&L from a list of trades.

        Realized P&L is calculated from closed positions (matched buy/sell pairs).
        """
        # Group trades by ticker
        ticker_trades: dict[str, list[Trade]] = {}
        for trade in trades:
            if trade.ticker not in ticker_trades:
                ticker_trades[trade.ticker] = []
            ticker_trades[trade.ticker].append(trade)

        total_realized = 0

        for ticker_trade_list in ticker_trades.values():
            # Sort by execution time
            sorted_trades = sorted(ticker_trade_list, key=lambda t: t.executed_at)

            # Track position for this ticker
            position_qty = 0
            position_cost = 0

            for trade in sorted_trades:
                if trade.action == "buy":
                    # Add to position
                    position_qty += trade.quantity
                    position_cost += trade.total_cost_cents + trade.fee_cents
                elif trade.action == "sell":
                    # Close position (FIFO)
                    if position_qty > 0:
                        # Calculate average cost per contract
                        avg_cost = position_cost / position_qty if position_qty > 0 else 0
                        # Realized gain/loss from this sale
                        realized = trade.total_cost_cents - (avg_cost * trade.quantity)
                        realized -= trade.fee_cents  # Subtract fees
                        total_realized += int(realized)

                        # Update position
                        position_qty -= trade.quantity
                        position_cost -= int(avg_cost * trade.quantity)

        return total_realized

    def calculate_total(self, positions: list[Position]) -> PnLSummary:
        """Calculate total P&L summary across all positions."""
        unrealized = sum(pos.unrealized_pnl_cents or 0 for pos in positions)
        realized = sum(pos.realized_pnl_cents for pos in positions)
        total = unrealized + realized

        # For now, return basic summary
        # Trade statistics require trade history
        return PnLSummary(
            unrealized_pnl_cents=unrealized,
            realized_pnl_cents=realized,
            total_pnl_cents=total,
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
        unrealized = sum(pos.unrealized_pnl_cents or 0 for pos in positions)
        realized = self.calculate_realized(trades)
        total = unrealized + realized

        # Calculate trade statistics
        closed_trades = self._get_closed_trades(trades)
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
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_win_cents=avg_win,
            avg_loss_cents=avg_loss,
            profit_factor=profit_factor,
        )

    def _get_closed_trades(self, trades: list[Trade]) -> list[int]:
        """Extract P&L from closed positions (matched buy/sell pairs)."""
        # Group trades by ticker and side
        ticker_sides: dict[tuple[str, str], list[Trade]] = {}
        for trade in trades:
            key = (trade.ticker, trade.side)
            if key not in ticker_sides:
                ticker_sides[key] = []
            ticker_sides[key].append(trade)

        closed_pnl: list[int] = []

        for side_trades in ticker_sides.values():
            sorted_trades = sorted(side_trades, key=lambda t: t.executed_at)

            position_qty = 0
            position_cost = 0

            for trade in sorted_trades:
                if trade.action == "buy":
                    position_qty += trade.quantity
                    position_cost += trade.total_cost_cents + trade.fee_cents
                elif trade.action == "sell":
                    if position_qty > 0:
                        avg_cost = position_cost / position_qty
                        pnl = int(
                            trade.total_cost_cents - (avg_cost * trade.quantity) - trade.fee_cents
                        )
                        closed_pnl.append(pnl)

                        position_qty -= trade.quantity
                        position_cost -= int(avg_cost * trade.quantity)

        return closed_pnl
