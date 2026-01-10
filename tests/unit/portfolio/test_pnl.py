"""Unit tests for P&L calculator."""

from datetime import UTC, datetime

from kalshi_research.portfolio.models import Position, Trade
from kalshi_research.portfolio.pnl import PnLCalculator, PnLSummary


class TestPnLCalculatorUnrealized:
    """Tests for unrealized P&L calculation."""

    def test_unrealized_yes_position_profit(self):
        """Test unrealized P&L for YES position with profit."""
        position = Position(
            ticker="TEST-TICKER",
            side="yes",
            quantity=100,
            avg_price_cents=45,  # Bought at 45¢
            opened_at=datetime.now(UTC),
            last_synced=datetime.now(UTC),
        )

        calculator = PnLCalculator()
        current_price = 52  # Now at 52¢
        pnl = calculator.calculate_unrealized(position, current_price)

        # (52 - 45) * 100 = 700 cents = $7.00
        assert pnl == 700

    def test_unrealized_yes_position_loss(self):
        """Test unrealized P&L for YES position with loss."""
        position = Position(
            ticker="TEST-TICKER",
            side="yes",
            quantity=100,
            avg_price_cents=55,  # Bought at 55¢
            opened_at=datetime.now(UTC),
            last_synced=datetime.now(UTC),
        )

        calculator = PnLCalculator()
        current_price = 48  # Now at 48¢
        pnl = calculator.calculate_unrealized(position, current_price)

        # (48 - 55) * 100 = -700 cents = -$7.00
        assert pnl == -700

    def test_unrealized_no_position_profit(self):
        """Test unrealized P&L for NO position with profit."""
        position = Position(
            ticker="TEST-TICKER",
            side="no",
            quantity=100,
            avg_price_cents=45,  # Bought NO at 45¢
            opened_at=datetime.now(UTC),
            last_synced=datetime.now(UTC),
        )

        calculator = PnLCalculator()
        current_price = 52  # NO now at 52¢
        pnl = calculator.calculate_unrealized(position, current_price)

        # NO position profits when NO contract price rises
        # (52 - 45) * 100 = 700 cents = $7.00
        assert pnl == 700

    def test_unrealized_no_position_loss(self):
        """Test unrealized P&L for NO position with loss."""
        position = Position(
            ticker="TEST-TICKER",
            side="no",
            quantity=100,
            avg_price_cents=55,  # Bought NO at 55¢
            opened_at=datetime.now(UTC),
            last_synced=datetime.now(UTC),
        )

        calculator = PnLCalculator()
        current_price = 48  # NO now at 48¢
        pnl = calculator.calculate_unrealized(position, current_price)

        # NO position loses when NO contract price falls
        # (48 - 55) * 100 = -700 cents = -$7.00
        assert pnl == -700


class TestPnLCalculatorRealized:
    """Tests for realized P&L calculation."""

    def test_summary_with_trades_skips_orphan_sells_instead_of_crashing(self) -> None:
        """BUG-058: Orphan sells (sell with no prior buys) must not crash the summary."""
        trades = [
            Trade(
                kalshi_trade_id="trade_orphan_sell",
                ticker="TEST-TICKER",
                side="yes",
                action="sell",
                quantity=10,
                price_cents=50,
                total_cost_cents=500,
                fee_cents=0,
                executed_at=datetime(2026, 1, 3, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            )
        ]

        calculator = PnLCalculator()
        summary = calculator.calculate_summary_with_trades(positions=[], trades=trades)

        assert summary.realized_pnl_cents == 0
        assert summary.total_trades == 0
        assert summary.orphan_sell_qty_skipped == 10

    def test_summary_with_trades_does_not_use_positions_realized_pnl_for_totals(self) -> None:
        """Total realized P&L is computed from synced history (fills + settlements)."""
        positions = [
            Position(
                ticker="TEST-TICKER",
                side="yes",
                quantity=1,
                avg_price_cents=40,
                current_price_cents=None,
                unrealized_pnl_cents=0,
                realized_pnl_cents=123,
                opened_at=datetime.now(UTC),
                last_synced=datetime.now(UTC),
            )
        ]
        trades = [
            Trade(
                kalshi_trade_id="trade_1",
                ticker="TEST-TICKER",
                side="yes",
                action="buy",
                quantity=1,
                price_cents=40,
                total_cost_cents=40,
                fee_cents=0,
                executed_at=datetime(2026, 1, 1, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
            Trade(
                kalshi_trade_id="trade_2",
                ticker="TEST-TICKER",
                side="yes",
                action="sell",
                quantity=1,
                price_cents=70,
                total_cost_cents=70,
                fee_cents=0,
                executed_at=datetime(2026, 1, 2, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
        ]

        calculator = PnLCalculator()
        summary = calculator.calculate_summary_with_trades(positions=positions, trades=trades)

        assert summary.realized_pnl_cents == 30
        assert summary.total_pnl_cents == 30  # unrealized is 0

    def test_realized_uses_fifo_across_multiple_buy_lots(self) -> None:
        """Realized P&L should use FIFO lots (not average cost)."""
        trades = [
            Trade(
                kalshi_trade_id="trade_1",
                ticker="TEST-TICKER",
                side="yes",
                action="buy",
                quantity=1,
                price_cents=40,
                total_cost_cents=40,
                fee_cents=0,
                executed_at=datetime(2026, 1, 1, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
            Trade(
                kalshi_trade_id="trade_2",
                ticker="TEST-TICKER",
                side="yes",
                action="buy",
                quantity=1,
                price_cents=60,
                total_cost_cents=60,
                fee_cents=0,
                executed_at=datetime(2026, 1, 2, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
            Trade(
                kalshi_trade_id="trade_3",
                ticker="TEST-TICKER",
                side="yes",
                action="sell",
                quantity=1,
                price_cents=70,
                total_cost_cents=70,
                fee_cents=0,
                executed_at=datetime(2026, 1, 3, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
        ]

        calculator = PnLCalculator()
        realized = calculator.calculate_realized(trades)

        # FIFO sells the first lot: buy 40 -> sell 70 = +30
        assert realized == 30

    def test_realized_fifo_partial_lot_no_floor_bias(self) -> None:
        """FIFO partial lot cost should round, not floor (BUG-056 audit fix)."""
        # Setup: buy 3 contracts at 101 cents total (33.67c each)
        # Then sell 1 at 50c
        # Floor: cost_basis = 101 * 1 // 3 = 33 → P&L = 50 - 33 = +17 (WRONG)
        # Round: cost_basis = round(101 * 1 / 3) = 34 → P&L = 50 - 34 = +16 (CORRECT)
        trades = [
            Trade(
                kalshi_trade_id="trade_1",
                ticker="TEST-TICKER",
                side="yes",
                action="buy",
                quantity=3,
                price_cents=34,  # avg ~33.67
                total_cost_cents=101,  # total cost is 101c
                fee_cents=0,
                executed_at=datetime(2026, 1, 1, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
            Trade(
                kalshi_trade_id="trade_2",
                ticker="TEST-TICKER",
                side="yes",
                action="sell",
                quantity=1,
                price_cents=50,
                total_cost_cents=50,
                fee_cents=0,
                executed_at=datetime(2026, 1, 2, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
        ]

        calculator = PnLCalculator()
        realized = calculator.calculate_realized(trades)

        # Should use round() not floor: round(101 * 1 / 3) = 34
        # P&L = 50 - 34 = 16
        assert realized == 16  # NOT 17 (which would indicate floor division bias)

    def test_realized_simple_buy_sell(self):
        """Test realized P&L from a simple buy-sell cycle."""
        trades = [
            Trade(
                kalshi_trade_id="trade_1",
                ticker="TEST-TICKER",
                side="yes",
                action="buy",
                quantity=100,
                price_cents=45,
                total_cost_cents=4500,
                fee_cents=225,
                executed_at=datetime(2026, 1, 1, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
            Trade(
                kalshi_trade_id="trade_2",
                ticker="TEST-TICKER",
                side="yes",
                action="sell",
                quantity=100,
                price_cents=52,
                total_cost_cents=5200,
                fee_cents=260,
                executed_at=datetime(2026, 1, 2, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
        ]

        calculator = PnLCalculator()
        realized = calculator.calculate_realized(trades)

        # Buy cost: 45*100 + 225 = 4725
        # Sell proceeds (net): 52*100 - 260 = 4940
        assert realized == 4940 - 4725

    def test_realized_partial_close(self):
        """Test realized P&L when partially closing a position."""
        trades = [
            Trade(
                kalshi_trade_id="trade_1",
                ticker="TEST-TICKER",
                side="yes",
                action="buy",
                quantity=200,
                price_cents=45,
                total_cost_cents=9000,
                fee_cents=450,
                executed_at=datetime(2026, 1, 1, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
            Trade(
                kalshi_trade_id="trade_2",
                ticker="TEST-TICKER",
                side="yes",
                action="sell",
                quantity=100,  # Sell half
                price_cents=52,
                total_cost_cents=5200,
                fee_cents=260,
                executed_at=datetime(2026, 1, 2, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
        ]

        calculator = PnLCalculator()
        realized = calculator.calculate_realized(trades)

        # Pro-rata cost basis for 100 contracts: (45*200 + 450) * 100 // 200 = 4725
        # Sell proceeds (net): 52*100 - 260 = 4940
        assert realized == 4940 - 4725

    def test_realized_does_not_mix_yes_no_cost_basis(self) -> None:
        """Test that YES and NO positions are treated as separate instruments."""
        trades = [
            # Buy YES and NO on the same ticker, then only close YES.
            Trade(
                kalshi_trade_id="trade_1",
                ticker="TEST-TICKER",
                side="yes",
                action="buy",
                quantity=100,
                price_cents=45,
                total_cost_cents=4500,
                fee_cents=225,
                executed_at=datetime(2026, 1, 1, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
            Trade(
                kalshi_trade_id="trade_2",
                ticker="TEST-TICKER",
                side="no",
                action="buy",
                quantity=100,
                price_cents=55,
                total_cost_cents=5500,
                fee_cents=275,
                executed_at=datetime(2026, 1, 1, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
            Trade(
                kalshi_trade_id="trade_3",
                ticker="TEST-TICKER",
                side="yes",
                action="sell",
                quantity=100,
                price_cents=52,
                total_cost_cents=5200,
                fee_cents=260,
                executed_at=datetime(2026, 1, 2, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
        ]

        calculator = PnLCalculator()
        realized = calculator.calculate_realized(trades)

        # Should only reflect the closed YES leg.
        assert realized == (5200 - 260) - (4500 + 225)

    def test_realized_multiple_tickers(self):
        """Test realized P&L across multiple tickers."""
        trades = [
            # Ticker 1: Profitable
            Trade(
                kalshi_trade_id="trade_1",
                ticker="TICKER-1",
                side="yes",
                action="buy",
                quantity=100,
                price_cents=45,
                total_cost_cents=4500,
                fee_cents=225,
                executed_at=datetime(2026, 1, 1, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
            Trade(
                kalshi_trade_id="trade_2",
                ticker="TICKER-1",
                side="yes",
                action="sell",
                quantity=100,
                price_cents=52,
                total_cost_cents=5200,
                fee_cents=260,
                executed_at=datetime(2026, 1, 2, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
            # Ticker 2: Loss
            Trade(
                kalshi_trade_id="trade_3",
                ticker="TICKER-2",
                side="yes",
                action="buy",
                quantity=100,
                price_cents=60,
                total_cost_cents=6000,
                fee_cents=300,
                executed_at=datetime(2026, 1, 1, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
            Trade(
                kalshi_trade_id="trade_4",
                ticker="TICKER-2",
                side="yes",
                action="sell",
                quantity=100,
                price_cents=55,
                total_cost_cents=5500,
                fee_cents=275,
                executed_at=datetime(2026, 1, 2, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
        ]

        calculator = PnLCalculator()
        realized = calculator.calculate_realized(trades)

        expected_ticker_1 = (5200 - 260) - (4500 + 225)
        expected_ticker_2 = (5500 - 275) - (6000 + 300)
        assert realized == expected_ticker_1 + expected_ticker_2


class TestPnLCalculatorSummary:
    """Tests for P&L summary generation."""

    def test_summary_basic(self):
        """Test basic P&L summary calculation."""
        positions = [
            Position(
                ticker="TICKER-1",
                side="yes",
                quantity=100,
                avg_price_cents=45,
                current_price_cents=52,
                unrealized_pnl_cents=700,
                realized_pnl_cents=0,
                opened_at=datetime.now(UTC),
                last_synced=datetime.now(UTC),
            ),
            Position(
                ticker="TICKER-2",
                side="no",
                quantity=50,
                avg_price_cents=55,
                current_price_cents=48,
                unrealized_pnl_cents=350,
                realized_pnl_cents=500,
                opened_at=datetime.now(UTC),
                last_synced=datetime.now(UTC),
            ),
        ]

        calculator = PnLCalculator()
        summary = calculator.calculate_total(positions)

        assert isinstance(summary, PnLSummary)
        assert summary.unrealized_pnl_cents == 1050  # 700 + 350
        assert summary.realized_pnl_cents == 500
        assert summary.total_pnl_cents == 1550  # 1050 + 500
        assert summary.unrealized_positions_unknown == 0

    def test_summary_with_trades_ignores_closed_positions_for_unrealized(self) -> None:
        """Closed positions must never contribute to unrealized P&L."""
        now = datetime.now(UTC)
        open_position = Position(
            ticker="OPEN",
            side="yes",
            quantity=10,
            avg_price_cents=50,
            current_price_cents=60,
            unrealized_pnl_cents=100,  # (60-50) * 10
            realized_pnl_cents=0,
            opened_at=now,
            last_synced=now,
        )
        closed_position = Position(
            ticker="CLOSED",
            side="yes",
            quantity=0,
            avg_price_cents=50,
            current_price_cents=60,
            unrealized_pnl_cents=None,
            realized_pnl_cents=0,
            opened_at=now,
            closed_at=now,
            last_synced=now,
        )

        calculator = PnLCalculator()
        summary = calculator.calculate_summary_with_trades(
            positions=[open_position, closed_position],
            trades=[],
        )

        assert summary.unrealized_pnl_cents == 100
        assert summary.unrealized_positions_unknown == 0

    def test_summary_with_none_values(self):
        """Test summary handles None values in unrealized P&L."""
        positions = [
            Position(
                ticker="TICKER-1",
                side="yes",
                quantity=100,
                avg_price_cents=45,
                current_price_cents=None,  # Not synced yet
                unrealized_pnl_cents=None,
                realized_pnl_cents=0,
                opened_at=datetime.now(UTC),
                last_synced=datetime.now(UTC),
            ),
        ]

        calculator = PnLCalculator()
        summary = calculator.calculate_total(positions)

        assert summary.unrealized_pnl_cents == 0  # Should handle None
        assert summary.realized_pnl_cents == 0
        assert summary.unrealized_positions_unknown == 1

    def test_summary_with_trades(self):
        """Test complete summary with trade statistics."""
        positions = [
            Position(
                ticker="TICKER-1",
                side="yes",
                quantity=100,
                avg_price_cents=45,
                current_price_cents=52,
                unrealized_pnl_cents=700,
                realized_pnl_cents=0,
                opened_at=datetime.now(UTC),
                last_synced=datetime.now(UTC),
            ),
        ]

        trades = [
            Trade(
                kalshi_trade_id="trade_1",
                ticker="TICKER-2",
                side="yes",
                action="buy",
                quantity=100,
                price_cents=45,
                total_cost_cents=4500,
                fee_cents=225,
                executed_at=datetime(2026, 1, 1, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
            Trade(
                kalshi_trade_id="trade_2",
                ticker="TICKER-2",
                side="yes",
                action="sell",
                quantity=100,
                price_cents=52,
                total_cost_cents=5200,
                fee_cents=260,
                executed_at=datetime(2026, 1, 2, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
        ]

        calculator = PnLCalculator()
        summary = calculator.calculate_summary_with_trades(positions, trades)

        assert isinstance(summary, PnLSummary)
        assert summary.unrealized_pnl_cents == 700
        assert summary.total_trades >= 0
        assert 0 <= summary.win_rate <= 1.0

    def test_summary_includes_portfolio_settlement_pnl(self) -> None:
        """BUG-059: Settlements should contribute to realized P&L and trade stats."""
        from kalshi_research.portfolio.models import PortfolioSettlement

        settlement = PortfolioSettlement(
            ticker="SETTLED-TICKER",
            event_ticker="EVENT-1",
            market_result="yes",
            yes_count=10,
            yes_total_cost=400,
            no_count=0,
            no_total_cost=0,
            revenue=1000,
            fee_cost_dollars="0.5000",
            value=None,
            settled_at=datetime(2026, 1, 5, tzinfo=UTC),
            synced_at=datetime.now(UTC),
        )

        calculator = PnLCalculator()
        summary = calculator.calculate_summary_with_trades(
            positions=[],
            trades=[],
            settlements=[settlement],
        )

        # P&L = revenue - cost - fees = 1000 - 400 - 50 = 550
        assert summary.realized_pnl_cents == 550
        assert summary.total_trades == 1
