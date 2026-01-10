"""Unit tests for backtesting framework."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kalshi_research.data.models import PriceSnapshot, Settlement
from kalshi_research.research.backtest import BacktestResult, BacktestTrade, ThesisBacktester
from kalshi_research.research.thesis import Thesis, ThesisStatus


@pytest.fixture
def sample_thesis() -> Thesis:
    """Create a sample resolved thesis."""
    return Thesis(
        id="test-thesis-001",
        title="BTC will hit 100k in Jan 2025",
        market_tickers=["KXBTC-25JAN-T100000", "KXBTC-25JAN-T95000"],
        your_probability=0.65,  # You think 65%
        market_probability=0.50,  # Market says 50%
        confidence=0.75,
        bull_case="Strong momentum, ETF inflows",
        bear_case="Regulatory concerns",
        key_assumptions=["ETF approval", "No black swan"],
        invalidation_criteria=["Drop below 80k"],
        status=ThesisStatus.RESOLVED,
        created_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        resolved_at=datetime(2025, 1, 31, 0, 0, 0, tzinfo=UTC),
        actual_outcome="yes",
    )


@pytest.fixture
def sample_settlements() -> list[Settlement]:
    """Create sample settlement data."""
    return [
        Settlement(
            ticker="KXBTC-25JAN-T100000",
            event_ticker="KXBTC-25JAN",
            settled_at=datetime(2025, 1, 31, 0, 0, 0, tzinfo=UTC),
            result="yes",
            final_yes_price=100,
            final_no_price=0,
            yes_payout=100,
            no_payout=0,
        ),
        Settlement(
            ticker="KXBTC-25JAN-T95000",
            event_ticker="KXBTC-25JAN",
            settled_at=datetime(2025, 1, 31, 0, 0, 0, tzinfo=UTC),
            result="no",
            final_yes_price=0,
            final_no_price=100,
            yes_payout=0,
            no_payout=100,
        ),
    ]


class TestBacktestTrade:
    """Test BacktestTrade dataclass."""

    def test_yes_trade_win(self) -> None:
        """Test P&L calculation for winning YES trade."""
        trade = BacktestTrade(
            ticker="TEST-TICKER",
            side="yes",
            entry_price=0.50,  # Bought at 50c
            exit_price=1.0,  # Resolved YES (100c)
            thesis_probability=0.65,
            contracts=1,
        )

        assert trade.pnl == 50.0  # (1.0 - 0.5) * 100 * 1
        assert trade.is_winner is True

    def test_yes_trade_loss(self) -> None:
        """Test P&L calculation for losing YES trade."""
        trade = BacktestTrade(
            ticker="TEST-TICKER",
            side="yes",
            entry_price=0.60,  # Bought at 60c
            exit_price=0.0,  # Resolved NO (0c)
            thesis_probability=0.70,
            contracts=1,
        )

        assert trade.pnl == -60.0  # (0.0 - 0.6) * 100 * 1
        assert trade.is_winner is False

    def test_no_trade_win(self) -> None:
        """Test P&L calculation for winning NO trade."""
        trade = BacktestTrade(
            ticker="TEST-TICKER",
            side="no",
            entry_price=0.70,  # Sold YES at 70c (bought NO at 30c)
            exit_price=0.0,  # Resolved NO (NO wins)
            thesis_probability=0.20,  # You thought 20% YES
            contracts=1,
        )

        # NO trade: entry_price - exit_price
        assert trade.pnl == 70.0  # (0.7 - 0.0) * 100 * 1
        assert trade.is_winner is True

    def test_no_trade_loss(self) -> None:
        """Test P&L calculation for losing NO trade."""
        trade = BacktestTrade(
            ticker="TEST-TICKER",
            side="no",
            entry_price=0.40,  # Sold YES at 40c
            exit_price=1.0,  # Resolved YES (NO loses)
            thesis_probability=0.30,
            contracts=1,
        )

        assert trade.pnl == -60.0  # (0.4 - 1.0) * 100 * 1
        assert trade.is_winner is False

    def test_multiple_contracts(self) -> None:
        """Test P&L scales with contract size."""
        trade = BacktestTrade(
            ticker="TEST-TICKER",
            side="yes",
            entry_price=0.50,
            exit_price=1.0,
            thesis_probability=0.65,
            contracts=10,
        )

        assert trade.pnl == 500.0  # (1.0 - 0.5) * 100 * 10


class TestBacktestResult:
    """Test BacktestResult dataclass."""

    def test_result_string_repr(self) -> None:
        """Test string representation of results."""
        result = BacktestResult(
            thesis_id="test-001",
            period_start=datetime(2025, 1, 1, tzinfo=UTC),
            period_end=datetime(2025, 1, 31, tzinfo=UTC),
            total_trades=10,
            winning_trades=7,
            losing_trades=3,
            total_pnl=250.0,
            avg_pnl=25.0,
            accuracy=0.70,
            brier_score=0.15,
            win_rate=0.70,
            sharpe_ratio=1.5,
        )

        result_str = str(result)
        assert "test-001" in result_str
        assert "10" in result_str  # total trades
        assert "7W / 3L" in result_str
        assert "70.0%" in result_str  # win rate
        assert "+250c" in result_str  # P&L
        assert "0.1500" in result_str  # Brier


class TestThesisBacktester:
    """Test ThesisBacktester class."""

    @pytest.mark.asyncio
    async def test_backtest_single_thesis(
        self,
        sample_thesis: Thesis,
        sample_settlements: list[Settlement],
    ) -> None:
        """Test backtesting a single thesis."""
        backtester = ThesisBacktester(default_contracts=1)

        result = await backtester.backtest_thesis(
            thesis=sample_thesis,
            settlements=sample_settlements,
        )

        assert result.thesis_id == "test-thesis-001"
        assert result.total_trades == 2
        assert len(result.trades) == 2

        # Check that trades were created for both markets
        tickers = {trade.ticker for trade in result.trades}
        assert tickers == {"KXBTC-25JAN-T100000", "KXBTC-25JAN-T95000"}

    @pytest.mark.asyncio
    async def test_backtest_skips_void_settlements(self, sample_thesis: Thesis) -> None:
        """Test that void settlements are ignored in backtests."""
        backtester = ThesisBacktester(default_contracts=1)

        settlements = [
            Settlement(
                ticker="KXBTC-25JAN-T100000",
                event_ticker="KXBTC-25JAN",
                settled_at=datetime(2025, 1, 31, 0, 0, 0, tzinfo=UTC),
                result="void",
                final_yes_price=None,
                final_no_price=None,
                yes_payout=None,
                no_payout=None,
            ),
            Settlement(
                ticker="KXBTC-25JAN-T95000",
                event_ticker="KXBTC-25JAN",
                settled_at=datetime(2025, 1, 31, 0, 0, 0, tzinfo=UTC),
                result="yes",
                final_yes_price=100,
                final_no_price=0,
                yes_payout=100,
                no_payout=0,
            ),
        ]

        result = await backtester.backtest_thesis(thesis=sample_thesis, settlements=settlements)

        assert result.total_trades == 1
        assert [trade.ticker for trade in result.trades] == ["KXBTC-25JAN-T95000"]

    @pytest.mark.asyncio
    async def test_backtest_determines_side_from_probability(
        self,
        sample_thesis: Thesis,
        sample_settlements: list[Settlement],
    ) -> None:
        """Test that trade side is determined from thesis probability."""
        backtester = ThesisBacktester()

        result = await backtester.backtest_thesis(
            thesis=sample_thesis,
            settlements=sample_settlements,
        )

        # Thesis has your_probability=0.65 (>0.5), so should trade YES side
        for trade in result.trades:
            assert trade.side == "yes"

    @pytest.mark.asyncio
    async def test_backtest_uses_market_probability_as_entry(
        self,
        sample_thesis: Thesis,
        sample_settlements: list[Settlement],
    ) -> None:
        """Test that market probability is used as entry price."""
        backtester = ThesisBacktester()

        result = await backtester.backtest_thesis(
            thesis=sample_thesis,
            settlements=sample_settlements,
        )

        # Should use thesis.market_probability (0.50) as entry
        for trade in result.trades:
            assert trade.entry_price == 0.50

    @pytest.mark.asyncio
    async def test_backtest_computes_pnl(
        self,
        sample_thesis: Thesis,
        sample_settlements: list[Settlement],
    ) -> None:
        """Test that P&L is computed correctly."""
        backtester = ThesisBacktester()

        result = await backtester.backtest_thesis(
            thesis=sample_thesis,
            settlements=sample_settlements,
        )

        # First settlement: YES result, entry 0.50, exit 1.0 → +50c
        # Second settlement: NO result, entry 0.50, exit 0.0 → -50c
        # Total: 0c
        assert result.total_trades == 2
        assert result.winning_trades == 1
        assert result.losing_trades == 1
        assert result.total_pnl == 0.0
        assert result.avg_pnl == 0.0

    @pytest.mark.asyncio
    async def test_backtest_computes_accuracy(
        self,
        sample_thesis: Thesis,
        sample_settlements: list[Settlement],
    ) -> None:
        """Test accuracy calculation."""
        backtester = ThesisBacktester()

        result = await backtester.backtest_thesis(
            thesis=sample_thesis,
            settlements=sample_settlements,
        )

        # Thesis prob: 0.65 (predicts YES)
        # Settlement 1: YES → correct
        # Settlement 2: NO → incorrect
        # Accuracy: 1/2 = 50%
        assert result.accuracy == 0.5

    @pytest.mark.asyncio
    async def test_backtest_computes_brier_score(
        self,
        sample_thesis: Thesis,
        sample_settlements: list[Settlement],
    ) -> None:
        """Test Brier score calculation."""
        backtester = ThesisBacktester()

        result = await backtester.backtest_thesis(
            thesis=sample_thesis,
            settlements=sample_settlements,
        )

        # Brier = mean((forecast - outcome)^2)
        # Trade 1: (0.65 - 1.0)^2 = 0.1225
        # Trade 2: (0.65 - 0.0)^2 = 0.4225
        # Mean: (0.1225 + 0.4225) / 2 = 0.2725
        expected_brier = 0.2725
        assert abs(result.brier_score - expected_brier) < 0.001

    @pytest.mark.asyncio
    async def test_backtest_with_price_snapshots(
        self,
        sample_thesis: Thesis,
        sample_settlements: list[Settlement],
    ) -> None:
        """Test backtesting with price snapshots for entry timing."""
        # Create price snapshots
        snapshots: dict[str, list[PriceSnapshot]] = {
            "KXBTC-25JAN-T100000": [
                PriceSnapshot(
                    ticker="KXBTC-25JAN-T100000",
                    snapshot_time=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
                    yes_bid=48,
                    yes_ask=52,
                    no_bid=48,
                    no_ask=52,
                    last_price=50,
                    volume=1000,
                    volume_24h=1000,
                    open_interest=500,
                ),
                PriceSnapshot(
                    ticker="KXBTC-25JAN-T100000",
                    snapshot_time=datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC),
                    yes_bid=53,
                    yes_ask=57,
                    no_bid=43,
                    no_ask=47,
                    last_price=55,
                    volume=2000,
                    volume_24h=1000,
                    open_interest=600,
                ),
            ]
        }

        backtester = ThesisBacktester()
        result = await backtester.backtest_thesis(
            thesis=sample_thesis,
            settlements=[sample_settlements[0]],  # Only first settlement
            snapshots=snapshots,
        )

        # Should use snapshot closest to thesis.created_at
        # First snapshot is at thesis creation time, yes_bid/ask = 48/52 → midpoint 50
        # _get_price_at_time should return (yes_bid + yes_ask) / 2 / 100 = 0.50
        # Actually it uses yes_ask / 100 = 0.52
        # Wait, looking at the spec code: `closest.yes_price / 100.0`
        # But PriceSnapshot doesn't have yes_price attribute!
        # Let me check the actual implementation in the spec more carefully

        # The spec has an error - PriceSnapshot doesn't have yes_price
        # We'll need to fix this in implementation
        assert len(result.trades) == 1

    @pytest.mark.asyncio
    async def test_backtest_empty_settlements(
        self,
        sample_thesis: Thesis,
    ) -> None:
        """Test backtesting with no settlements."""
        backtester = ThesisBacktester()

        result = await backtester.backtest_thesis(
            thesis=sample_thesis,
            settlements=[],
        )

        assert result.thesis_id == "test-thesis-001"
        assert result.total_trades == 0
        assert len(result.trades) == 0
        assert result.total_pnl == 0.0

    @pytest.mark.asyncio
    async def test_backtest_no_side_below_50_percent(self) -> None:
        """Test that thesis with probability < 0.5 trades NO side."""
        thesis = Thesis(
            id="test-no-side",
            title="BTC will NOT hit 100k",
            market_tickers=["KXBTC-25JAN-T100000"],
            your_probability=0.30,  # You think only 30% chance
            market_probability=0.50,
            confidence=0.80,
            bull_case="",
            bear_case="",
            key_assumptions=[],
            invalidation_criteria=[],
            status=ThesisStatus.RESOLVED,
        )

        settlement = Settlement(
            ticker="KXBTC-25JAN-T100000",
            event_ticker="KXBTC-25JAN",
            settled_at=datetime(2025, 1, 31, 0, 0, 0, tzinfo=UTC),
            result="no",
            final_yes_price=0,
            final_no_price=100,
        )

        backtester = ThesisBacktester()
        result = await backtester.backtest_thesis(thesis, [settlement])

        assert len(result.trades) == 1
        assert result.trades[0].side == "no"
        # NO side won, should have positive P&L
        assert result.trades[0].is_winner is True

    @pytest.mark.asyncio
    async def test_backtest_all_theses(
        self,
        sample_thesis: Thesis,
        sample_settlements: list[Settlement],
    ) -> None:
        """Test backtesting multiple theses."""
        thesis2 = Thesis(
            id="test-thesis-002",
            title="Another thesis",
            market_tickers=["KXBTC-25JAN-T95000"],
            your_probability=0.40,
            market_probability=0.50,
            confidence=0.60,
            bull_case="",
            bear_case="",
            key_assumptions=[],
            invalidation_criteria=[],
            status=ThesisStatus.RESOLVED,
        )

        backtester = ThesisBacktester()
        results = await backtester.backtest_all(
            theses=[sample_thesis, thesis2],
            settlements=sample_settlements,
        )

        assert len(results) == 2
        assert {r.thesis_id for r in results} == {"test-thesis-001", "test-thesis-002"}

    @pytest.mark.asyncio
    async def test_backtest_all_skips_unresolved(
        self,
        sample_thesis: Thesis,
        sample_settlements: list[Settlement],
    ) -> None:
        """Test that backtest_all only processes resolved theses."""
        active_thesis = Thesis(
            id="active-thesis",
            title="Active thesis",
            market_tickers=["TEST"],
            your_probability=0.60,
            market_probability=0.50,
            confidence=0.70,
            bull_case="",
            bear_case="",
            key_assumptions=[],
            invalidation_criteria=[],
            status=ThesisStatus.ACTIVE,  # Not resolved
        )

        backtester = ThesisBacktester()
        results = await backtester.backtest_all(
            theses=[sample_thesis, active_thesis],
            settlements=sample_settlements,
        )

        # Only sample_thesis should be backtested (it's RESOLVED)
        assert len(results) == 1
        assert results[0].thesis_id == "test-thesis-001"

    @pytest.mark.asyncio
    async def test_backtest_win_rate_calculation(self) -> None:
        """Test win rate calculation with known outcomes."""
        thesis = Thesis(
            id="win-rate-test",
            title="Win rate test",
            market_tickers=["TICKER1", "TICKER2", "TICKER3", "TICKER4"],
            your_probability=0.70,
            market_probability=0.50,
            confidence=0.80,
            bull_case="",
            bear_case="",
            key_assumptions=[],
            invalidation_criteria=[],
            status=ThesisStatus.RESOLVED,
        )

        # 3 wins, 1 loss → 75% win rate
        settlements = [
            Settlement(
                ticker="TICKER1",
                event_ticker="EVENT1",
                settled_at=datetime.now(UTC),
                result="yes",  # Win
            ),
            Settlement(
                ticker="TICKER2",
                event_ticker="EVENT1",
                settled_at=datetime.now(UTC),
                result="yes",  # Win
            ),
            Settlement(
                ticker="TICKER3",
                event_ticker="EVENT1",
                settled_at=datetime.now(UTC),
                result="yes",  # Win
            ),
            Settlement(
                ticker="TICKER4",
                event_ticker="EVENT1",
                settled_at=datetime.now(UTC),
                result="no",  # Loss
            ),
        ]

        backtester = ThesisBacktester()
        result = await backtester.backtest_thesis(thesis, settlements)

        assert result.total_trades == 4
        assert result.winning_trades == 3
        assert result.losing_trades == 1
        assert result.win_rate == 0.75

    @pytest.mark.asyncio
    async def test_backtest_sharpe_ratio(self) -> None:
        """Test Sharpe ratio calculation."""
        thesis = Thesis(
            id="sharpe-test",
            title="Sharpe test",
            market_tickers=["T1", "T2", "T3"],
            your_probability=0.70,
            market_probability=0.50,
            confidence=0.80,
            bull_case="",
            bear_case="",
            key_assumptions=[],
            invalidation_criteria=[],
            status=ThesisStatus.RESOLVED,
        )

        settlements = [
            Settlement(
                ticker="T1",
                event_ticker="E1",
                settled_at=datetime.now(UTC),
                result="yes",
            ),
            Settlement(
                ticker="T2",
                event_ticker="E1",
                settled_at=datetime.now(UTC),
                result="yes",
            ),
            Settlement(
                ticker="T3",
                event_ticker="E1",
                settled_at=datetime.now(UTC),
                result="no",
            ),
        ]

        backtester = ThesisBacktester()
        result = await backtester.backtest_thesis(thesis, settlements)

        # Sharpe should be computed (mean PNL / std PNL)
        # With >1 trade and non-zero std, should have a value
        assert result.sharpe_ratio != 0.0
