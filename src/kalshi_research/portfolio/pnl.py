"""P&L (Profit and Loss) calculator for portfolio positions.

Settlement handling follows Kalshi's documented behavior:
    "Settlements act as 'sells' at the settlement price (100c if won, 0c if lost)"
    - kalshi-api-reference.md:917

This means settlements are treated as synthetic closing fills at the binary outcome price,
processed through the same FIFO logic as regular trades.

Note on fees:
    Kalshi's fills API does not include per-fill fees. The settlement record includes `fee_cost`
    as a fixed-point dollar string; empirically this represents total trading fees for the
    ticker (not a separate "settlement fee"). We apply these fees once at the end of the
    realized P&L calculation to avoid double-counting and to cover positions closed via trades.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from kalshi_research.portfolio._fifo import get_closed_trade_pnls_fifo, normalize_trade_for_fifo
from kalshi_research.portfolio._pnl_models import EffectiveTrade, FifoResult, Lot, PnLSummary
from kalshi_research.portfolio._settlements import (
    get_settlement_prices_cents,
    parse_settlement_fee_cents,
    process_synthetic_fills,
    synthesize_settlement_closes,
)

if TYPE_CHECKING:
    from kalshi_research.portfolio.models import PortfolioSettlement, Position, Trade

# Re-export for backwards compatibility
__all__ = ["PnLCalculator", "PnLSummary"]


class PnLCalculator:
    """Calculate profit/loss on positions and trades."""

    # Re-expose internal types for backwards compatibility with tests
    _Lot = Lot
    _EffectiveTrade = EffectiveTrade
    _FifoResult = FifoResult

    @staticmethod
    def _round_div_half_up(numerator: int, denominator: int) -> int:
        """Round numerator/denominator to nearest int with half-up semantics."""
        if denominator <= 0:
            raise ValueError("denominator must be positive")

        if numerator >= 0:
            return (numerator + (denominator // 2)) // denominator
        return -((-numerator + (denominator // 2)) // denominator)

    @staticmethod
    def _normalize_trade_for_fifo(trade: Trade) -> EffectiveTrade:
        """Normalize fills into a consistent (ticker, side) stream for FIFO.

        Delegates to the module-level function for the actual implementation.
        """
        return normalize_trade_for_fifo(trade)

    def _get_closed_trade_pnls_fifo(self, trades: list[Trade]) -> FifoResult:
        """Compute per-sell realized P&L in cents using FIFO lots (integer arithmetic).

        Delegates to the module-level function for the actual implementation.
        """
        return get_closed_trade_pnls_fifo(trades)

    def _synthesize_settlement_closes(
        self,
        settlements: list[PortfolioSettlement],
        open_lots: dict[tuple[str, str], Lot],
    ) -> list[EffectiveTrade]:
        """Convert settlements to synthetic closing fills for remaining open lots.

        Delegates to the module-level function for the actual implementation.
        """
        return synthesize_settlement_closes(settlements, open_lots)

    def _process_synthetic_fills(
        self,
        synthetic_fills: list[EffectiveTrade],
        open_lots: dict[tuple[str, str], Lot],
    ) -> list[int]:
        """Process synthetic settlement fills against open lots to compute P&L.

        Delegates to the module-level function for the actual implementation.
        """
        return process_synthetic_fills(synthetic_fills, open_lots)

    @staticmethod
    def _get_settlement_prices_cents(
        market_result: str, settlement_value: int | None
    ) -> tuple[int, int] | None:
        """Get (yes_price_cents, no_price_cents) at settlement, or None if not supported.

        Delegates to the settlements module for the actual implementation.
        """
        return get_settlement_prices_cents(market_result, settlement_value)

    @staticmethod
    def _parse_settlement_fee_cents(fee_cost_dollars: str) -> int:
        """Parse trading fees from settlement `fee_cost_dollars` into integer cents.

        Delegates to the settlements module for the actual implementation.
        """
        return parse_settlement_fee_cents(fee_cost_dollars)

    def calculate_unrealized(self, position: Position, current_price_cents: int) -> int:
        """
        Calculate unrealized P&L for a position in cents.

        Prices in this codebase are stored in contract cents for the position side (YES or NO).
        Unrealized P&L is therefore always:

            (current_price - avg_price) * quantity
        """
        return (current_price_cents - position.avg_price_cents) * position.quantity

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
        """
        Calculate complete P&L summary including trade statistics.

        Settlement handling per Kalshi docs (kalshi-api-reference.md:917):
            "Settlements act as 'sells' at the settlement price (100c if won, 0c if lost)"

        For any open lots remaining after processing trades, settlements are converted
        to synthetic closing fills at the binary outcome price (100c or 0c), then
        processed through the same FIFO logic.
        """
        open_positions = [pos for pos in positions if pos.closed_at is None and pos.quantity > 0]
        unrealized_positions_unknown = sum(
            1 for pos in open_positions if pos.unrealized_pnl_cents is None
        )
        unrealized = sum(
            pos.unrealized_pnl_cents
            for pos in open_positions
            if pos.unrealized_pnl_cents is not None
        )

        # Step 1: Process all trades via FIFO
        fifo_result = self._get_closed_trade_pnls_fifo(trades)

        # Step 2: Synthesize settlement closes for remaining open lots
        # Per SSOT: settlements are synthetic sells at settlement price
        settlement_pnls: list[int] = []
        settlement_trading_fees_cents = 0
        if settlements:
            trades_tickers = {trade.ticker for trade in trades}
            position_tickers = {pos.ticker for pos in positions}
            settlement_tickers_with_holdings = {
                settlement.ticker
                for settlement in settlements
                if settlement.yes_count > 0 or settlement.no_count > 0
            }
            relevant_fee_tickers = (
                trades_tickers | position_tickers | settlement_tickers_with_holdings
            )

            settlement_trading_fees_cents = sum(
                self._parse_settlement_fee_cents(settlement.fee_cost_dollars)
                for settlement in settlements
                if settlement.ticker in relevant_fee_tickers
            )

            # Build effective open lots: start with FIFO results, then add implicit
            # lots for settlements without corresponding trades (handles data gaps)
            effective_open_lots = dict(fifo_result.open_lots)

            for settlement in settlements:
                if settlement.ticker not in trades_tickers:
                    # No trades for this ticker - create implicit lots from settlement
                    # This handles the case where fills weren't synced but settlements were
                    if settlement.yes_count > 0:
                        effective_open_lots[(settlement.ticker, "yes")] = Lot(
                            qty_remaining=settlement.yes_count,
                            cost_remaining_cents=settlement.yes_total_cost,
                        )
                    if settlement.no_count > 0:
                        effective_open_lots[(settlement.ticker, "no")] = Lot(
                            qty_remaining=settlement.no_count,
                            cost_remaining_cents=settlement.no_total_cost,
                        )

            if effective_open_lots:
                synthetic_fills = self._synthesize_settlement_closes(
                    settlements, effective_open_lots
                )
                # Process synthetic fills against effective lots
                settlement_pnls = self._process_synthetic_fills(
                    synthetic_fills, effective_open_lots
                )

        # Combine trade P&Ls and settlement P&Ls
        closed_trades = fifo_result.closed_pnls + settlement_pnls

        realized = sum(closed_trades) - settlement_trading_fees_cents
        total = unrealized + realized

        winning = [t for t in closed_trades if t > 0]
        losing = [t for t in closed_trades if t < 0]

        total_trades = len(closed_trades)
        winning_trades = len(winning)
        losing_trades = len(losing)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        avg_win = self._round_div_half_up(sum(winning), len(winning)) if winning else 0
        avg_loss = abs(self._round_div_half_up(sum(losing), len(losing))) if losing else 0
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
