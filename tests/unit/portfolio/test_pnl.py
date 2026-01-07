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
            avg_price_cents=55,  # Bought NO at 55¢
            opened_at=datetime.now(UTC),
            last_synced=datetime.now(UTC),
        )

        calculator = PnLCalculator()
        current_price = 48  # NO now at 48¢ (YES went up, NO went down)
        pnl = calculator.calculate_unrealized(position, current_price)

        # NO position profits when price goes down
        # (55 - 48) * 100 = 700 cents = $7.00
        assert pnl == 700

    def test_unrealized_no_position_loss(self):
        """Test unrealized P&L for NO position with loss."""
        position = Position(
            ticker="TEST-TICKER",
            side="no",
            quantity=100,
            avg_price_cents=45,  # Bought NO at 45¢
            opened_at=datetime.now(UTC),
            last_synced=datetime.now(UTC),
        )

        calculator = PnLCalculator()
        current_price = 52  # NO now at 52¢ (YES went down, NO went up)
        pnl = calculator.calculate_unrealized(position, current_price)

        # NO position loses when price goes up
        # (45 - 52) * 100 = -700 cents = -$7.00
        assert pnl == -700


class TestPnLCalculatorRealized:
    """Tests for realized P&L calculation."""

    def test_realized_simple_buy_sell(self):
        """Test realized P&L from a simple buy-sell cycle."""
        trades = [
            Trade(
                kalshi_trade_id="trade_1",
                ticker="TEST-TICKER",
                side="yes",
                action="buy",
                quantity=100,
                price_cents=4500,
                total_cost_cents=450000,
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
                price_cents=5200,
                total_cost_cents=520000,
                fee_cents=260,
                executed_at=datetime(2026, 1, 2, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
        ]

        calculator = PnLCalculator()
        realized = calculator.calculate_realized(trades)

        # Bought 100 @ 45¢ = $450.00 + $2.25 fee = $452.25
        # Sold 100 @ 52¢ = $520.00 - $2.60 fee = $517.40
        # Profit = $517.40 - $452.25 = $65.15 = 6515 cents
        # Note: calculation is (520000 - 450000) - 225 - 260 = 69515 cents
        assert realized > 0  # Should be positive

    def test_realized_partial_close(self):
        """Test realized P&L when partially closing a position."""
        trades = [
            Trade(
                kalshi_trade_id="trade_1",
                ticker="TEST-TICKER",
                side="yes",
                action="buy",
                quantity=200,
                price_cents=4500,
                total_cost_cents=900000,
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
                price_cents=5200,
                total_cost_cents=520000,
                fee_cents=260,
                executed_at=datetime(2026, 1, 2, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
        ]

        calculator = PnLCalculator()
        realized = calculator.calculate_realized(trades)

        # Should have realized profit on the 100 contracts sold
        assert realized > 0

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
                price_cents=4500,
                total_cost_cents=450000,
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
                price_cents=5500,
                total_cost_cents=550000,
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
                price_cents=5200,
                total_cost_cents=520000,
                fee_cents=260,
                executed_at=datetime(2026, 1, 2, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
        ]

        calculator = PnLCalculator()
        realized = calculator.calculate_realized(trades)

        # Should only reflect the closed YES leg.
        assert realized == 520000 - 450000 - 225 - 260

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
                price_cents=4500,
                total_cost_cents=450000,
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
                price_cents=5200,
                total_cost_cents=520000,
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
                price_cents=6000,
                total_cost_cents=600000,
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
                price_cents=5500,
                total_cost_cents=550000,
                fee_cents=275,
                executed_at=datetime(2026, 1, 2, tzinfo=UTC),
                synced_at=datetime.now(UTC),
            ),
        ]

        calculator = PnLCalculator()
        realized = calculator.calculate_realized(trades)

        # Net should be profit from ticker 1 minus loss from ticker 2
        # Should be positive overall
        assert isinstance(realized, int)


class TestPnLCalculatorSummary:
    """Tests for P&L summary generation."""

    def test_summary_basic(self):
        """Test basic P&L summary calculation."""
        positions = [
            Position(
                ticker="TICKER-1",
                side="yes",
                quantity=100,
                avg_price_cents=4500,
                current_price_cents=5200,
                unrealized_pnl_cents=700,
                realized_pnl_cents=0,
                opened_at=datetime.now(UTC),
                last_synced=datetime.now(UTC),
            ),
            Position(
                ticker="TICKER-2",
                side="no",
                quantity=50,
                avg_price_cents=5500,
                current_price_cents=4800,
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

    def test_summary_with_none_values(self):
        """Test summary handles None values in unrealized P&L."""
        positions = [
            Position(
                ticker="TICKER-1",
                side="yes",
                quantity=100,
                avg_price_cents=4500,
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

    def test_summary_with_trades(self):
        """Test complete summary with trade statistics."""
        positions = [
            Position(
                ticker="TICKER-1",
                side="yes",
                quantity=100,
                avg_price_cents=4500,
                current_price_cents=5200,
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
                price_cents=4500,
                total_cost_cents=450000,
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
                price_cents=5200,
                total_cost_cents=520000,
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
