# SPEC-008: Research Notebooks & Backtesting

**Status:** ✅ Implemented
**Priority:** P2 (Explicitly requested: notebooks/, backtesting)
**Estimated Complexity:** Medium
**Dependencies:** SPEC-002 through SPEC-007 (all previous specs)

---

## Implementation References

- `notebooks/`
- `src/kalshi_research/research/backtest.py`
- `src/kalshi_research/research/notebook_utils.py`

---

## 1. Overview

Create Jupyter notebook templates and a backtesting framework for thesis validation. The user explicitly requested `notebooks/` for exploration and `research.py` for thesis testing/backtesting.

### 1.1 Goals

- Jupyter notebook templates for common research workflows
- Notebook utility functions for data loading and display
- Thesis backtesting against historical data
- Calculate hypothetical P&L from past predictions
- Track thesis accuracy over time

### 1.2 Non-Goals

- Production trading backtester with realistic fills
- Complex portfolio backtesting
- Automated notebook execution
- nbconvert automation

---

## 2. Core Concepts

### 2.1 Notebook Workflows

| Notebook | Purpose |
|----------|---------|
| `01_exploration.ipynb` | Initial data exploration, market discovery |
| `02_calibration.ipynb` | Calibration analysis, Brier scores |
| `03_edge_detection.ipynb` | Finding edges, thesis development |
| `templates/market_analysis.ipynb` | Reusable template for any market |

### 2.2 Backtesting Framework

Test your thesis against historical data:

1. **Define thesis** at a point in time
2. **Apply thesis** to historical market prices
3. **Calculate hypothetical P&L** if you had traded
4. **Measure accuracy** vs random/naive baseline

### 2.3 Backtest Metrics

| Metric | Description |
|--------|-------------|
| **Accuracy** | % of predictions correct |
| **Brier Score** | Quality of probability estimates |
| **Hypothetical P&L** | What you would have made/lost |
| **Sharpe Ratio** | Risk-adjusted returns (simplified) |
| **Win Rate** | % of trades profitable |

---

## 3. Technical Specification

### 3.1 Directory Structure

```
notebooks/
├── 01_exploration.ipynb        # Data exploration
├── 02_calibration.ipynb        # Calibration analysis
├── 03_edge_detection.ipynb     # Edge detection
└── templates/
    └── market_analysis.ipynb   # Reusable template

src/kalshi_research/
├── research/
│   ├── __init__.py
│   ├── thesis.py               # EXISTS
│   ├── backtest.py             # NEW - Backtesting framework
│   └── notebook_utils.py       # NEW - Jupyter helpers
```

### 3.2 Backtest Module

```python
# src/kalshi_research/research/backtest.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Sequence
import numpy as np

from kalshi_research.research.thesis import Thesis, ThesisStatus
from kalshi_research.data.models import PriceSnapshot, SettlementModel


@dataclass
class BacktestTrade:
    """A simulated trade from backtesting."""

    ticker: str
    side: str                   # "yes" or "no"
    entry_price: float          # Price when thesis created (0-1)
    exit_price: float           # Settlement price (0 or 1)
    thesis_probability: float   # Your probability estimate
    contracts: int = 1          # Simulated position size

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
    total_pnl: float = 0.0      # Total P&L in cents
    avg_pnl: float = 0.0        # Average P&L per trade
    max_win: float = 0.0
    max_loss: float = 0.0

    # Accuracy metrics
    accuracy: float = 0.0       # % predictions correct
    brier_score: float = 0.0    # Brier score of predictions
    win_rate: float = 0.0       # % of trades profitable

    # Risk metrics
    sharpe_ratio: float = 0.0   # Simplified Sharpe

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
        settlements: Sequence[SettlementModel],
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
        relevant_settlements = [
            s for s in settlements
            if s.ticker in thesis.market_tickers
        ]

        for settlement in relevant_settlements:
            # Determine entry price (market prob at thesis creation)
            if snapshots and settlement.ticker in snapshots:
                # Use closest snapshot to thesis creation
                entry_price = self._get_price_at_time(
                    snapshots[settlement.ticker],
                    thesis.created_at,
                )
            else:
                entry_price = thesis.market_probability

            # Determine exit price from settlement
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
        settlements: Sequence[SettlementModel],
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

        closest = min(
            snapshots,
            key=lambda s: abs((s.timestamp - target_time).total_seconds())
        )
        return closest.yes_price / 100.0

    def _compute_result(
        self,
        thesis_id: str,
        trades: list[BacktestTrade],
    ) -> BacktestResult:
        """Compute metrics from trades."""
        if not trades:
            return BacktestResult(
                thesis_id=thesis_id,
                period_start=datetime.now(timezone.utc),
                period_end=datetime.now(timezone.utc),
            )

        pnls = [t.pnl for t in trades]
        forecasts = [t.thesis_probability for t in trades]
        outcomes = [t.exit_price for t in trades]

        total_pnl = sum(pnls)
        winning = [t for t in trades if t.is_winner]
        losing = [t for t in trades if not t.is_winner]

        # Brier score
        brier = float(np.mean([
            (f - o) ** 2 for f, o in zip(forecasts, outcomes)
        ]))

        # Accuracy (prediction > 0.5 matches outcome)
        correct = sum(
            1 for f, o in zip(forecasts, outcomes)
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
            period_start=datetime.now(timezone.utc),  # Would use actual dates
            period_end=datetime.now(timezone.utc),
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
```

### 3.3 Notebook Utilities Module

```python
# src/kalshi_research/research/notebook_utils.py
"""
Jupyter notebook utilities for Kalshi research.

Usage:
    from kalshi_research.research.notebook_utils import setup_notebook, load_markets

    setup_notebook()  # Configure display settings
    markets = await load_markets()  # Load market data
"""
import asyncio
from typing import Any

import pandas as pd
from IPython.display import display, HTML
from rich.console import Console
from rich.table import Table

from kalshi_research.api import KalshiPublicClient
from kalshi_research.api.models import Market
from kalshi_research.analysis.edge import Edge
from kalshi_research.data import DatabaseManager


def setup_notebook(
    pd_max_rows: int = 100,
    pd_max_cols: int = 20,
    figure_format: str = "retina",
) -> None:
    """
    Configure notebook display settings.

    Args:
        pd_max_rows: Max pandas rows to display
        pd_max_cols: Max pandas columns to display
        figure_format: Matplotlib figure format (retina for HiDPI)
    """
    # Pandas display options
    pd.set_option("display.max_rows", pd_max_rows)
    pd.set_option("display.max_columns", pd_max_cols)
    pd.set_option("display.width", 1000)
    pd.set_option("display.float_format", "{:.4f}".format)

    # Matplotlib settings
    try:
        import matplotlib.pyplot as plt
        from IPython import get_ipython

        ipython = get_ipython()
        if ipython:
            ipython.run_line_magic("matplotlib", "inline")
            ipython.run_line_magic("config", f"InlineBackend.figure_format = '{figure_format}'")

        plt.style.use("seaborn-v0_8-whitegrid")
        plt.rcParams["figure.figsize"] = (12, 6)
        plt.rcParams["font.size"] = 12
    except ImportError:
        pass

    print("Notebook configured for Kalshi research.")


async def load_markets(
    status: str = "open",
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Load markets into a pandas DataFrame.

    Args:
        status: Market status filter (open, closed, settled)
        limit: Max markets to load

    Returns:
        DataFrame with market data
    """
    async with KalshiPublicClient() as client:
        markets: list[dict[str, Any]] = []
        count = 0

        async for market in client.get_all_markets(status=status):
            markets.append({
                "ticker": market.ticker,
                "title": market.title,
                "subtitle": market.subtitle,
                "yes_price": market.yes_price / 100.0,
                "yes_bid": market.yes_bid,
                "yes_ask": market.yes_ask,
                "spread": market.yes_ask - market.yes_bid,
                "volume": market.volume,
                "open_interest": market.open_interest,
                "close_time": market.close_time,
                "status": market.status,
                "event_ticker": market.event_ticker,
            })

            count += 1
            if limit and count >= limit:
                break

    return pd.DataFrame(markets)


async def load_events(limit: int | None = None) -> pd.DataFrame:
    """Load events into a DataFrame."""
    async with KalshiPublicClient() as client:
        events: list[dict[str, Any]] = []
        count = 0

        async for event in client.get_all_events():
            events.append({
                "event_ticker": event.event_ticker,
                "title": event.title,
                "category": event.category,
                "mutually_exclusive": event.mutually_exclusive,
            })

            count += 1
            if limit and count >= limit:
                break

    return pd.DataFrame(events)


def display_market(market: Market) -> None:
    """
    Rich display of a single market in Jupyter.

    Args:
        market: Market to display
    """
    html = f"""
    <div style="border: 1px solid #ddd; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <h3 style="margin-top: 0;">{market.ticker}</h3>
        <p><strong>{market.title}</strong></p>
        <p><em>{market.subtitle}</em></p>
        <table style="width: 100%;">
            <tr>
                <td><strong>YES Price:</strong></td>
                <td>{market.yes_price}c ({market.yes_price/100:.0%})</td>
                <td><strong>Volume:</strong></td>
                <td>{market.volume:,}</td>
            </tr>
            <tr>
                <td><strong>Bid/Ask:</strong></td>
                <td>{market.yes_bid}c / {market.yes_ask}c (spread: {market.yes_ask - market.yes_bid}c)</td>
                <td><strong>Open Interest:</strong></td>
                <td>{market.open_interest:,}</td>
            </tr>
            <tr>
                <td><strong>Status:</strong></td>
                <td>{market.status}</td>
                <td><strong>Closes:</strong></td>
                <td>{market.close_time.strftime('%Y-%m-%d %H:%M UTC') if market.close_time else 'N/A'}</td>
            </tr>
        </table>
    </div>
    """
    display(HTML(html))


def display_edge(edge: Edge) -> None:
    """
    Rich display of a detected edge in Jupyter.

    Args:
        edge: Edge to display
    """
    yours = f"{edge.your_estimate:.0%}" if edge.your_estimate else "N/A"
    ev = f"{edge.expected_value:+.1f}c" if edge.expected_value else "N/A"

    color = "green" if (edge.expected_value or 0) > 0 else "red"

    html = f"""
    <div style="border: 2px solid {color}; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <h4 style="margin-top: 0; color: {color};">[{edge.edge_type.value.upper()}] {edge.ticker}</h4>
        <table style="width: 100%;">
            <tr>
                <td><strong>Market Price:</strong></td>
                <td>{edge.market_price:.0%}</td>
                <td><strong>Your Estimate:</strong></td>
                <td>{yours}</td>
            </tr>
            <tr>
                <td><strong>Expected Value:</strong></td>
                <td style="color: {color}; font-weight: bold;">{ev}</td>
                <td><strong>Confidence:</strong></td>
                <td>{edge.confidence:.0%}</td>
            </tr>
        </table>
        <p style="margin-bottom: 0;"><em>{edge.description}</em></p>
    </div>
    """
    display(HTML(html))


def display_markets_table(
    markets: list[Market] | pd.DataFrame,
    columns: list[str] | None = None,
) -> None:
    """
    Display markets in a Rich table format.

    Args:
        markets: List of markets or DataFrame
        columns: Columns to include (defaults to key columns)
    """
    if columns is None:
        columns = ["ticker", "title", "yes_price", "spread", "volume", "status"]

    if isinstance(markets, pd.DataFrame):
        df = markets
    else:
        df = pd.DataFrame([
            {
                "ticker": m.ticker,
                "title": m.title[:50] + "..." if len(m.title) > 50 else m.title,
                "yes_price": f"{m.yes_price}c",
                "spread": f"{m.yes_ask - m.yes_bid}c",
                "volume": f"{m.volume:,}",
                "status": m.status,
            }
            for m in markets
        ])

    display(df[columns].head(20))


# Helper for running async in notebooks
def run_async(coro: Any) -> Any:
    """
    Run async coroutine in notebook.

    Usage:
        markets = run_async(load_markets())
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context (e.g., Jupyter with async enabled)
            import nest_asyncio
            nest_asyncio.apply()
        return asyncio.run(coro)
    except RuntimeError:
        return asyncio.run(coro)
```

### 3.4 Notebook Templates

#### 01_exploration.ipynb

```python
# Cell 1: Setup
from kalshi_research.research.notebook_utils import setup_notebook, load_markets
setup_notebook()

# Cell 2: Load data
markets = await load_markets(status="open", limit=500)
print(f"Loaded {len(markets)} markets")

# Cell 3: Basic statistics
print(f"Total volume: {markets['volume'].sum():,}")
print(f"Avg spread: {markets['spread'].mean():.1f}c")
print(f"Markets near 50%: {len(markets[(markets['yes_price'] > 0.4) & (markets['yes_price'] < 0.6)])}")

# Cell 4: Top markets by volume
markets.nlargest(20, 'volume')[['ticker', 'title', 'yes_price', 'volume']]

# Cell 5: Price distribution
import matplotlib.pyplot as plt
markets['yes_price'].hist(bins=20, edgecolor='black')
plt.xlabel('Probability')
plt.ylabel('Count')
plt.title('Distribution of Market Prices')
```

#### 02_calibration.ipynb

```python
# Cell 1: Setup
from kalshi_research.research.notebook_utils import setup_notebook
from kalshi_research.analysis.calibration import CalibrationAnalyzer
from kalshi_research.analysis.visualization import plot_calibration_curve
setup_notebook()

# Cell 2: Load settlements
# ... load settlement data ...

# Cell 3: Compute calibration
analyzer = CalibrationAnalyzer(n_bins=10)
result = analyzer.compute_calibration(forecasts, outcomes)
print(result)

# Cell 4: Plot calibration curve
fig = plot_calibration_curve(result, title="Kalshi Market Calibration")
plt.show()
```

#### 03_edge_detection.ipynb

```python
# Cell 1: Setup and thesis
from kalshi_research.research.notebook_utils import setup_notebook, display_edge
from kalshi_research.analysis.edge import EdgeDetector
from kalshi_research.analysis.scanner import MarketScanner
setup_notebook()

# Cell 2: Define your thesis
# Your estimate for a specific market
my_estimates = {
    "KXBTC-25JAN-T100000": 0.65,  # You think 65%, market says lower
    # ... more markets ...
}

# Cell 3: Detect edges
detector = EdgeDetector()
for ticker, my_prob in my_estimates.items():
    market = await get_market(ticker)
    edge = detector.detect_thesis_edge(
        ticker=ticker,
        market_prob=market.yes_price / 100.0,
        your_prob=my_prob,
    )
    if edge:
        display_edge(edge)

# Cell 4: Scan for opportunities
scanner = MarketScanner()
close_races = scanner.scan_close_races(markets, top_n=10)
# ... display results ...
```

---

## 4. Implementation Tasks

### 4.1 Phase 1: Backtest Module

- [ ] Implement `BacktestTrade` dataclass
- [ ] Implement `BacktestResult` dataclass
- [ ] Implement `ThesisBacktester` class
- [ ] Write unit tests for backtesting

### 4.2 Phase 2: Notebook Utilities

- [ ] Implement `setup_notebook()`
- [ ] Implement `load_markets()`, `load_events()`
- [ ] Implement `display_market()`, `display_edge()`
- [ ] Implement `run_async()` helper
- [ ] Write tests for utilities

### 4.3 Phase 3: Notebook Templates

- [ ] Create `notebooks/` directory
- [ ] Create `01_exploration.ipynb`
- [ ] Create `02_calibration.ipynb`
- [ ] Create `03_edge_detection.ipynb`
- [ ] Create `templates/market_analysis.ipynb`
- [ ] Verify all notebooks run without errors

### 4.4 Phase 4: CLI Integration

- [ ] Add `kalshi research backtest` command
- [ ] Add thesis backtest export

---

## 5. Acceptance Criteria

1. **Backtest**: Correctly compute P&L and accuracy for resolved theses
2. **Metrics**: Brier score, win rate, Sharpe all compute correctly
3. **Notebooks**: All 4 notebooks run without errors
4. **Utilities**: `setup_notebook()` configures display properly
5. **Display**: Market and edge display renders correctly in Jupyter
6. **Tests**: >85% coverage on backtest and notebook_utils

---

## 6. Usage Examples

```python
# Backtesting usage
from kalshi_research.research.backtest import ThesisBacktester
from kalshi_research.research.thesis import Thesis

backtester = ThesisBacktester(default_contracts=10)

# Backtest a thesis
result = await backtester.backtest_thesis(thesis, settlements)
print(result)
# Output:
# Backtest Results (thesis-001):
#   Period: 2025-01-01 to 2025-12-31
#   Trades: 15 (10W / 5L)
#   Win Rate: 66.7%
#   Total P&L: +1250c
#   Avg P&L: +83.3c/trade
#   Brier Score: 0.1823
#   Accuracy: 73.3%

# Backtest all theses
results = await backtester.backtest_all(all_theses, settlements)
for r in sorted(results, key=lambda x: x.total_pnl, reverse=True):
    print(f"{r.thesis_id}: {r.total_pnl:+.0f}c ({r.win_rate:.0%} win rate)")
```

```python
# Notebook utilities usage
from kalshi_research.research.notebook_utils import (
    setup_notebook,
    load_markets,
    display_market,
)

setup_notebook()

# Load and explore markets
markets_df = await load_markets(status="open")
markets_df.describe()

# Display single market
market = await get_market("KXBTC-25JAN-T100000")
display_market(market)
```

---

## 7. Future Considerations

- Interactive widgets for thesis parameters
- Backtest with realistic slippage and fees
- Monte Carlo simulation of thesis outcomes
- Export notebooks to HTML reports
- Automated notebook scheduling
- Integration with nbconvert for PDF generation
- Backtest against live paper trading
