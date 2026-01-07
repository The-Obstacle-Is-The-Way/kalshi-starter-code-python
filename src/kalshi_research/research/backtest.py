"""Backtesting framework for research theses."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import numpy as np

from kalshi_research.data.models import PriceSnapshot, Settlement
from kalshi_research.research.thesis import Thesis, ThesisStatus


@dataclass
class BacktestTrade:
    """A simulated trade from backtesting."""

    ticker: str
    side: str  # "yes" or "no"
    entry_price: float  # Price when thesis created (0-1)
    exit_price: float  # Settlement price (0 or 1)
    thesis_probability: float  # Your probability estimate
    contracts: int = 1  # Simulated position size

    @property
    def pnl(self) -> float:
        """Profit/loss in cents per contract."""
        if self.side == "yes":
            return (self.exit_price - self.entry_price) * 100 * self.contracts
        else:
            return (self.entry_price - self.exit_price) * 100 * self.contracts

    @property
    def is_winner(self) -> bool:
        """Did this trade make money?"""
        return self.pnl > 0


@dataclass
class BacktestResult:
    """Results from backtesting a thesis or set of theses."""

    thesis_id: str
    period_start: datetime
    period_end: datetime

    # Trade statistics
    trades: list[BacktestTrade] = field(default_factory=list)
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0

    # P&L
    total_pnl: float = 0.0  # Total P&L in cents
    avg_pnl: float = 0.0  # Average P&L per trade
    max_win: float = 0.0
    max_loss: float = 0.0

    # Accuracy metrics
    accuracy: float = 0.0  # % predictions correct
    brier_score: float = 0.0  # Brier score of predictions
    win_rate: float = 0.0  # % of trades profitable

    # Risk metrics
    sharpe_ratio: float = 0.0  # Simplified Sharpe

    def __str__(self) -> str:
        return (
            f"Backtest Results ({self.thesis_id}):\n"
            f"  Period: {self.period_start.date()} to {self.period_end.date()}\n"
            f"  Trades: {self.total_trades} ({self.winning_trades}W / {self.losing_trades}L)\n"
            f"  Win Rate: {self.win_rate:.1%}\n"
            f"  Total P&L: {self.total_pnl:+.0f}c\n"
            f"  Avg P&L: {self.avg_pnl:+.1f}c/trade\n"
            f"  Brier Score: {self.brier_score:.4f}\n"
            f"  Accuracy: {self.accuracy:.1%}"
        )


class ThesisBacktester:
    """
    Backtest research theses against historical data.

    Usage:
        backtester = ThesisBacktester()
        result = await backtester.backtest_thesis(thesis, settlements)
    """

    def __init__(
        self,
        default_contracts: int = 1,
        include_spreads: bool = False,
    ) -> None:
        """
        Initialize backtester.

        Args:
            default_contracts: Default position size per thesis
            include_spreads: Whether to simulate bid-ask spread costs
        """
        self.default_contracts = default_contracts
        self.include_spreads = include_spreads

    async def backtest_thesis(
        self,
        thesis: Thesis,
        settlements: Sequence[Settlement],
        snapshots: dict[str, Sequence[PriceSnapshot]] | None = None,
    ) -> BacktestResult:
        """
        Backtest a single thesis against historical settlements.

        Args:
            thesis: The thesis to backtest
            settlements: Historical settlement data
            snapshots: Optional price snapshots for entry timing

        Returns:
            BacktestResult with performance metrics
        """
        trades: list[BacktestTrade] = []

        # Filter settlements for thesis markets
        relevant_settlements = [s for s in settlements if s.ticker in thesis.market_tickers]

        for settlement in relevant_settlements:
            # Skip void settlements - they don't affect P&L calculations
            if settlement.result == "void":
                continue

            # Determine entry price (market prob at thesis creation)
            if snapshots and settlement.ticker in snapshots:
                # Use closest snapshot to thesis creation
                entry_price = self._get_price_at_time(
                    snapshots[settlement.ticker],
                    thesis.created_at,
                )
            else:
                entry_price = thesis.market_probability

            # Determine exit price from settlement (yes=1.0, no=0.0)
            exit_price = 1.0 if settlement.result == "yes" else 0.0

            # Determine trade side from thesis
            if thesis.your_probability > 0.5:
                side = "yes"
            else:
                side = "no"

            trade = BacktestTrade(
                ticker=settlement.ticker,
                side=side,
                entry_price=entry_price,
                exit_price=exit_price,
                thesis_probability=thesis.your_probability,
                contracts=self.default_contracts,
            )
            trades.append(trade)

        return self._compute_result(thesis.id, trades)

    async def backtest_all(
        self,
        theses: Sequence[Thesis],
        settlements: Sequence[Settlement],
        snapshots: dict[str, Sequence[PriceSnapshot]] | None = None,
    ) -> list[BacktestResult]:
        """
        Backtest multiple theses.

        Args:
            theses: List of theses to backtest
            settlements: Historical settlement data
            snapshots: Optional price snapshots

        Returns:
            List of BacktestResults
        """
        results: list[BacktestResult] = []

        for thesis in theses:
            if thesis.status == ThesisStatus.RESOLVED:
                result = await self.backtest_thesis(thesis, settlements, snapshots)
                results.append(result)

        return results

    def _get_price_at_time(
        self,
        snapshots: Sequence[PriceSnapshot],
        target_time: datetime,
    ) -> float:
        """Get price closest to target time."""
        if not snapshots:
            return 0.5  # Default to 50%

        closest = min(snapshots, key=lambda s: abs((s.snapshot_time - target_time).total_seconds()))
        # Use midpoint of bid/ask as price
        return closest.midpoint / 100.0

    def _compute_result(
        self,
        thesis_id: str,
        trades: list[BacktestTrade],
    ) -> BacktestResult:
        """Compute metrics from trades."""
        if not trades:
            return BacktestResult(
                thesis_id=thesis_id,
                period_start=datetime.now(UTC),
                period_end=datetime.now(UTC),
            )

        pnls = [t.pnl for t in trades]
        forecasts = [t.thesis_probability for t in trades]
        outcomes = [t.exit_price for t in trades]

        total_pnl = sum(pnls)
        winning = [t for t in trades if t.is_winner]
        losing = [t for t in trades if not t.is_winner]

        # Brier score
        brier = float(np.mean([(f - o) ** 2 for f, o in zip(forecasts, outcomes)]))

        # Accuracy (prediction > 0.5 matches outcome)
        correct = sum(
            1
            for f, o in zip(forecasts, outcomes)
            if (f > 0.5 and o == 1.0) or (f < 0.5 and o == 0.0)
        )
        accuracy = correct / len(forecasts) if forecasts else 0.0

        # Sharpe ratio (simplified)
        if len(pnls) > 1 and np.std(pnls) > 0:
            sharpe = float(np.mean(pnls) / np.std(pnls))
        else:
            sharpe = 0.0

        return BacktestResult(
            thesis_id=thesis_id,
            period_start=datetime.now(UTC),  # Would use actual dates
            period_end=datetime.now(UTC),
            trades=trades,
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            total_pnl=total_pnl,
            avg_pnl=total_pnl / len(trades) if trades else 0.0,
            max_win=max(pnls) if pnls else 0.0,
            max_loss=min(pnls) if pnls else 0.0,
            accuracy=accuracy,
            brier_score=brier,
            win_rate=len(winning) / len(trades) if trades else 0.0,
            sharpe_ratio=sharpe,
        )
