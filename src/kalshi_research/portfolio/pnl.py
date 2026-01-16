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
        open_lots: dict[tuple[str, str], PnLCalculator._Lot]

    @staticmethod
    def _get_settlement_prices_cents(
        market_result: str, settlement_value: int | None
    ) -> tuple[int, int] | None:
        """
        Get (yes_price_cents, no_price_cents) at settlement, or None if not supported.

        Per Kalshi docs, binary settlements are at 100c/0c. For scalar markets, the API
        provides `settlement_value` as the YES payout in cents, and NO pays (100 - value).
        """
        if market_result == "yes":
            return 100, 0
        if market_result == "no":
            return 0, 100
        if market_result != "scalar":
            return None
        if settlement_value is None or settlement_value < 0 or settlement_value > 100:
            return None
        return settlement_value, 100 - settlement_value

    @staticmethod
    def _parse_settlement_fee_cents(fee_cost_dollars: str) -> int:
        """Parse trading fees from settlement `fee_cost_dollars` into integer cents."""
        try:
            return int(
                (Decimal(fee_cost_dollars) * 100).to_integral_value(rounding=ROUND_HALF_EVEN)
            )
        except (InvalidOperation, ValueError):
            return 0

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

    def _synthesize_settlement_closes(
        self,
        settlements: list[PortfolioSettlement],
        open_lots: dict[tuple[str, str], _Lot],
    ) -> list[_EffectiveTrade]:
        """
        Convert settlements to synthetic closing fills for remaining open lots.

        Per Kalshi docs (kalshi-api-reference.md:917):
            "Settlements act as 'sells' at the settlement price (100c if won, 0c if lost)"

        This treats settlements as synthetic sells at the binary outcome price:
        - market_result='yes' -> YES contracts sell at 100c, NO contracts sell at 0c
        - market_result='no'  -> YES contracts sell at 0c, NO contracts sell at 100c
        - market_result='void' -> No P&L impact (positions refunded at cost)

        Args:
            settlements: List of portfolio settlements from Kalshi API
            open_lots: Dict of (ticker, side) -> Lot with remaining open positions

        Returns:
            List of synthetic closing fills.
        """
        synthetic_fills: list[PnLCalculator._EffectiveTrade] = []

        for settlement in settlements:
            prices = self._get_settlement_prices_cents(settlement.market_result, settlement.value)
            if prices is None:
                continue
            yes_settlement_price, no_settlement_price = prices

            yes_key = (settlement.ticker, "yes")
            yes_qty = (
                open_lots[yes_key].qty_remaining
                if yes_key in open_lots and open_lots[yes_key].qty_remaining > 0
                else 0
            )
            no_key = (settlement.ticker, "no")
            no_qty = (
                open_lots[no_key].qty_remaining
                if no_key in open_lots and open_lots[no_key].qty_remaining > 0
                else 0
            )

            total_qty = yes_qty + no_qty
            if total_qty <= 0:
                continue

            # Synthesize YES fill if open YES lots exist for this ticker
            if yes_qty > 0:
                synthetic_fills.append(
                    PnLCalculator._EffectiveTrade(
                        ticker=settlement.ticker,
                        side="yes",
                        action="sell",
                        quantity=yes_qty,
                        price_cents=yes_settlement_price,
                        total_cost_cents=yes_settlement_price * yes_qty,
                        fee_cents=0,
                        executed_at=settlement.settled_at,
                    )
                )

            # Synthesize NO fill if open NO lots exist for this ticker
            if no_qty > 0:
                synthetic_fills.append(
                    PnLCalculator._EffectiveTrade(
                        ticker=settlement.ticker,
                        side="no",
                        action="sell",
                        quantity=no_qty,
                        price_cents=no_settlement_price,
                        total_cost_cents=no_settlement_price * no_qty,
                        fee_cents=0,
                        executed_at=settlement.settled_at,
                    )
                )

        return synthetic_fills

    def _process_synthetic_fills(
        self,
        synthetic_fills: list[_EffectiveTrade],
        open_lots: dict[tuple[str, str], _Lot],
    ) -> list[int]:
        """
        Process synthetic settlement fills against open lots to compute P&L.

        Uses the same FIFO logic as regular trades but operates on the mutable
        open_lots dict from the initial trade processing.

        Args:
            synthetic_fills: Synthetic closing fills from settlements
            open_lots: Mutable dict of open lots (will be consumed)

        Returns:
            List of P&L values for each synthetic close
        """
        closed_pnls: list[int] = []

        for fill in synthetic_fills:
            key = (fill.ticker, fill.side)
            if key not in open_lots:
                continue

            lot = open_lots[key]
            if lot.qty_remaining <= 0:
                continue

            # Consume from the lot (settlement closes all remaining)
            consume_qty = min(lot.qty_remaining, fill.quantity)
            if consume_qty == 0:
                continue

            # Pro-rata cost basis
            consume_cost_cents = round(lot.cost_remaining_cents * consume_qty / lot.qty_remaining)

            # Calculate P&L: proceeds - cost - fees
            # Fee is prorated to consumed quantity
            matched_fee_cents = round(fill.fee_cents * consume_qty / fill.quantity)
            net_proceeds_cents = (fill.price_cents * consume_qty) - matched_fee_cents
            pnl = net_proceeds_cents - consume_cost_cents
            closed_pnls.append(pnl)

            # Update lot
            lot.cost_remaining_cents -= consume_cost_cents
            lot.qty_remaining -= consume_qty

        return closed_pnls

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

        open_lots: dict[tuple[str, str], PnLCalculator._Lot] = {}

        for key, group_trades in ticker_side_trades.items():
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

            if not lots:
                continue

            qty_remaining = sum(lot.qty_remaining for lot in lots)
            cost_remaining = sum(lot.cost_remaining_cents for lot in lots)
            if qty_remaining <= 0:
                continue

            open_lots[key] = PnLCalculator._Lot(
                qty_remaining=qty_remaining, cost_remaining_cents=cost_remaining
            )

        return PnLCalculator._FifoResult(
            closed_pnls=closed_pnls,
            orphan_sell_qty_skipped=orphan_sell_qty_skipped,
            open_lots=open_lots,
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
            settlement_trading_fees_cents = sum(
                self._parse_settlement_fee_cents(settlement.fee_cost_dollars)
                for settlement in settlements
            )

            # Build effective open lots: start with FIFO results, then add implicit
            # lots for settlements without corresponding trades (handles data gaps)
            effective_open_lots = dict(fifo_result.open_lots)
            trades_tickers = {trade.ticker for trade in trades}

            for settlement in settlements:
                if settlement.ticker not in trades_tickers:
                    # No trades for this ticker - create implicit lots from settlement
                    # This handles the case where fills weren't synced but settlements were
                    if settlement.yes_count > 0:
                        effective_open_lots[(settlement.ticker, "yes")] = PnLCalculator._Lot(
                            qty_remaining=settlement.yes_count,
                            cost_remaining_cents=settlement.yes_total_cost,
                        )
                    if settlement.no_count > 0:
                        effective_open_lots[(settlement.ticker, "no")] = PnLCalculator._Lot(
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
