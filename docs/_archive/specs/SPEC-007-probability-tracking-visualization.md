# SPEC-007: Probability Tracking & Visualization

**Status:** ✅ Implemented
**Priority:** P2 (Explicitly requested: "Probability Tracker - Track how market probabilities change over time")
**Estimated Complexity:** Medium
**Dependencies:** SPEC-002 (API Client), SPEC-003 (Data Layer), SPEC-004 (Analysis)

---

## Implementation References

- `src/kalshi_research/analysis/metrics.py`
- `src/kalshi_research/analysis/visualization.py`

---

## 1. Overview

Implement probability tracking over time and visualization tools for research analysis. This includes tracking price movements, generating charts, and computing market efficiency metrics.

### 1.1 Goals

- Track probability changes over time for any market
- Generate publication-quality charts (calibration curves, probability timelines, edge histograms)
- Compute market efficiency metrics (spread, depth, volatility)
- Export charts for notebooks and reports
- CLI commands for quick visualization

### 1.2 Non-Goals

- Real-time streaming dashboards
- Interactive web-based visualizations
- TradingView-style candlestick charts
- Custom chart styling beyond matplotlib defaults

---

## 2. Core Concepts

### 2.1 Probability Tracking

Track how market probabilities evolve:
- Price history over time
- Volume at each price point
- Spread evolution
- Key events (settlements, news catalysts)

### 2.2 Market Efficiency Metrics

| Metric | Description | Calculation |
|--------|-------------|-------------|
| **Spread** | Cost of immediacy | Ask - Bid (in cents) |
| **Relative Spread** | Normalized spread | Spread / MidPrice |
| **Depth** | Liquidity available | Volume at best bid + ask |
| **Volatility** | Price movement | Std dev of returns |
| **Volume Profile** | Trading activity | Volume by time of day |

### 2.3 Visualization Types

1. **Calibration Curve**: Predicted vs actual frequencies
2. **Probability Timeline**: Price over time
3. **Edge Histogram**: Distribution of detected edges
4. **Spread Chart**: Bid-ask spread over time
5. **Volume Profile**: Heatmap of volume by time

---

## 3. Technical Specification

### 3.1 Module Structure

```
src/kalshi_research/
├── analysis/
│   ├── metrics.py         # Market efficiency metrics
│   └── visualization.py   # Chart generation
```

### 3.2 Metrics Module

```python
# src/kalshi_research/analysis/metrics.py
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import numpy as np
from typing import Sequence

from kalshi_research.api.models import Market
from kalshi_research.data.models import PriceSnapshot


@dataclass
class SpreadStats:
    """Spread statistics for a market."""

    ticker: str
    current_spread: int         # Current bid-ask spread (cents)
    avg_spread: float           # Average spread over period
    min_spread: int             # Minimum spread seen
    max_spread: int             # Maximum spread seen
    relative_spread: float      # Spread / midpoint
    n_samples: int


@dataclass
class VolatilityStats:
    """Volatility statistics for a market."""

    ticker: str
    daily_volatility: float     # Annualized daily vol
    hourly_volatility: float    # Hourly vol
    max_daily_move: float       # Largest single-day move
    avg_abs_return: float       # Average absolute return
    period_days: int


@dataclass
class VolumeProfile:
    """Volume distribution over time."""

    ticker: str
    hourly_volume: dict[int, float]     # Hour (0-23) -> avg volume
    daily_volume: dict[str, float]      # Weekday -> avg volume
    total_volume: int
    period_days: int


class MarketMetrics:
    """
    Compute market efficiency and trading metrics.

    Usage:
        metrics = MarketMetrics()
        spread = metrics.compute_spread_stats(market, snapshots)
        vol = metrics.compute_volatility(snapshots)
    """

    def compute_spread_stats(
        self,
        market: Market,
        snapshots: Sequence[PriceSnapshot] | None = None,
    ) -> SpreadStats:
        """
        Compute spread statistics.

        Args:
            market: Current market data
            snapshots: Historical snapshots (optional, for averages)

        Returns:
            SpreadStats with current and historical spread info
        """
        current_spread = market.yes_ask - market.yes_bid
        midpoint = (market.yes_ask + market.yes_bid) / 2.0

        if snapshots and len(snapshots) > 0:
            spreads = [s.yes_ask - s.yes_bid for s in snapshots]
            avg_spread = float(np.mean(spreads))
            min_spread = min(spreads)
            max_spread = max(spreads)
            n_samples = len(snapshots)
        else:
            avg_spread = float(current_spread)
            min_spread = current_spread
            max_spread = current_spread
            n_samples = 1

        relative_spread = current_spread / midpoint if midpoint > 0 else 0.0

        return SpreadStats(
            ticker=market.ticker,
            current_spread=current_spread,
            avg_spread=avg_spread,
            min_spread=min_spread,
            max_spread=max_spread,
            relative_spread=relative_spread,
            n_samples=n_samples,
        )

    def compute_volatility(
        self,
        snapshots: Sequence[PriceSnapshot],
        annualize: bool = True,
    ) -> VolatilityStats | None:
        """
        Compute volatility statistics from price snapshots.

        Args:
            snapshots: Historical price snapshots
            annualize: Whether to annualize volatility

        Returns:
            VolatilityStats or None if insufficient data
        """
        if len(snapshots) < 2:
            return None

        ticker = snapshots[0].ticker

        # Sort by timestamp
        sorted_snaps = sorted(snapshots, key=lambda s: s.timestamp)

        # Compute returns
        prices = [s.yes_price / 100.0 for s in sorted_snaps]
        returns = np.diff(prices) / np.array(prices[:-1])

        # Handle edge cases (0 prices)
        returns = returns[np.isfinite(returns)]

        if len(returns) < 2:
            return None

        # Compute stats
        hourly_vol = float(np.std(returns))

        # Time span for annualization
        time_span = (sorted_snaps[-1].timestamp - sorted_snaps[0].timestamp)
        period_days = max(1, time_span.days)

        # Annualize (assuming ~8760 hours/year)
        if annualize:
            daily_vol = hourly_vol * np.sqrt(24)
        else:
            daily_vol = hourly_vol

        # Daily returns for max move
        daily_returns = self._compute_daily_returns(sorted_snaps)
        max_daily = max(abs(r) for r in daily_returns) if daily_returns else 0.0

        return VolatilityStats(
            ticker=ticker,
            daily_volatility=daily_vol,
            hourly_volatility=hourly_vol,
            max_daily_move=max_daily,
            avg_abs_return=float(np.mean(np.abs(returns))),
            period_days=period_days,
        )

    def compute_volume_profile(
        self,
        snapshots: Sequence[PriceSnapshot],
    ) -> VolumeProfile | None:
        """
        Compute volume distribution by time of day and day of week.

        Args:
            snapshots: Historical snapshots with volume data

        Returns:
            VolumeProfile or None if no data
        """
        if not snapshots:
            return None

        ticker = snapshots[0].ticker

        # Group by hour
        hourly: dict[int, list[int]] = {h: [] for h in range(24)}
        daily: dict[str, list[int]] = {
            "Mon": [], "Tue": [], "Wed": [], "Thu": [], "Fri": [], "Sat": [], "Sun": []
        }
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        for snap in snapshots:
            hour = snap.timestamp.hour
            weekday = day_names[snap.timestamp.weekday()]
            vol = snap.volume if hasattr(snap, 'volume') else 0

            hourly[hour].append(vol)
            daily[weekday].append(vol)

        # Compute averages
        hourly_avg = {h: float(np.mean(v)) if v else 0.0 for h, v in hourly.items()}
        daily_avg = {d: float(np.mean(v)) if v else 0.0 for d, v in daily.items()}

        time_span = max(s.timestamp for s in snapshots) - min(s.timestamp for s in snapshots)

        return VolumeProfile(
            ticker=ticker,
            hourly_volume=hourly_avg,
            daily_volume=daily_avg,
            total_volume=sum(s.volume for s in snapshots if hasattr(s, 'volume')),
            period_days=max(1, time_span.days),
        )

    def _compute_daily_returns(
        self,
        snapshots: Sequence[PriceSnapshot],
    ) -> list[float]:
        """Compute daily returns from snapshots."""
        # Group by date
        by_date: dict[str, list[float]] = {}
        for snap in snapshots:
            date_key = snap.timestamp.date().isoformat()
            if date_key not in by_date:
                by_date[date_key] = []
            by_date[date_key].append(snap.yes_price / 100.0)

        # Compute daily close-to-close returns
        dates = sorted(by_date.keys())
        returns: list[float] = []

        for i in range(1, len(dates)):
            prev_close = by_date[dates[i - 1]][-1]
            curr_close = by_date[dates[i]][-1]
            if prev_close > 0:
                returns.append((curr_close - prev_close) / prev_close)

        return returns
```

### 3.3 Visualization Module

```python
# src/kalshi_research/analysis/visualization.py
from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from matplotlib.figure import Figure

from kalshi_research.analysis.calibration import CalibrationResult
from kalshi_research.analysis.edge import Edge
from kalshi_research.data.models import PriceSnapshot


def plot_calibration_curve(
    result: CalibrationResult,
    title: str = "Calibration Curve",
    save_path: Path | str | None = None,
) -> Figure:
    """
    Plot calibration curve showing predicted vs actual probabilities.

    Args:
        result: CalibrationResult from CalibrationAnalyzer
        title: Chart title
        save_path: Optional path to save figure

    Returns:
        Matplotlib Figure
    """
    fig, ax = plt.subplots(figsize=(8, 6))

    # Perfect calibration line
    ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Perfect calibration")

    # Filter valid bins
    valid = ~np.isnan(result.predicted_probs) & ~np.isnan(result.actual_freqs)
    predicted = result.predicted_probs[valid]
    actual = result.actual_freqs[valid]
    counts = result.bin_counts[valid]

    # Plot calibration curve with point sizes based on sample count
    sizes = np.sqrt(counts) * 5  # Scale for visibility
    scatter = ax.scatter(
        predicted,
        actual,
        s=sizes,
        c="blue",
        alpha=0.7,
        label="Observed"
    )

    # Annotations
    ax.set_xlabel("Predicted Probability")
    ax.set_ylabel("Actual Frequency")
    ax.set_title(f"{title}\n(Brier Score: {result.brier_score:.4f}, n={result.n_samples})")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Add size legend
    handles, labels = scatter.legend_elements(
        prop="sizes", num=4, alpha=0.6,
        func=lambda s: (s / 5) ** 2  # Reverse the sqrt scaling
    )
    ax.legend(handles, labels, title="Samples", loc="upper left")

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_probability_timeline(
    snapshots: Sequence[PriceSnapshot],
    title: str | None = None,
    save_path: Path | str | None = None,
) -> Figure:
    """
    Plot probability over time for a market.

    Args:
        snapshots: Price snapshots for a single market
        title: Chart title (defaults to ticker)
        save_path: Optional path to save figure

    Returns:
        Matplotlib Figure
    """
    if not snapshots:
        raise ValueError("No snapshots provided")

    # Sort by timestamp
    sorted_snaps = sorted(snapshots, key=lambda s: s.timestamp)
    ticker = sorted_snaps[0].ticker

    timestamps = [s.timestamp for s in sorted_snaps]
    prices = [s.yes_price / 100.0 for s in sorted_snaps]

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(timestamps, prices, "b-", linewidth=1.5)
    ax.fill_between(timestamps, prices, alpha=0.2)

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())

    ax.set_xlabel("Date")
    ax.set_ylabel("Probability")
    ax.set_title(title or f"Probability Timeline: {ticker}")
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)

    plt.xticks(rotation=45)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_edge_histogram(
    edges: Sequence[Edge],
    title: str = "Edge Distribution",
    save_path: Path | str | None = None,
) -> Figure:
    """
    Plot histogram of detected edges.

    Args:
        edges: List of detected edges
        title: Chart title
        save_path: Optional path to save figure

    Returns:
        Matplotlib Figure
    """
    if not edges:
        raise ValueError("No edges provided")

    # Extract edge sizes (your estimate - market price)
    edge_sizes = [
        (e.your_estimate or 0.5) - e.market_price
        for e in edges
        if e.your_estimate is not None
    ]

    if not edge_sizes:
        raise ValueError("No edges with estimates")

    fig, ax = plt.subplots(figsize=(10, 6))

    # Histogram
    bins = np.linspace(-0.5, 0.5, 21)
    n, bins_out, patches = ax.hist(
        edge_sizes,
        bins=bins,
        edgecolor="black",
        alpha=0.7
    )

    # Color positive/negative differently
    for i, patch in enumerate(patches):
        if bins_out[i] >= 0:
            patch.set_facecolor("green")
        else:
            patch.set_facecolor("red")

    ax.axvline(0, color="black", linestyle="--", alpha=0.5)
    ax.set_xlabel("Edge Size (Your Estimate - Market)")
    ax.set_ylabel("Count")
    ax.set_title(f"{title}\n(n={len(edge_sizes)}, mean={np.mean(edge_sizes):.1%})")
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_spread_timeline(
    snapshots: Sequence[PriceSnapshot],
    title: str | None = None,
    save_path: Path | str | None = None,
) -> Figure:
    """
    Plot bid-ask spread over time.

    Args:
        snapshots: Price snapshots with bid/ask data
        title: Chart title
        save_path: Optional path to save figure

    Returns:
        Matplotlib Figure
    """
    if not snapshots:
        raise ValueError("No snapshots provided")

    sorted_snaps = sorted(snapshots, key=lambda s: s.timestamp)
    ticker = sorted_snaps[0].ticker

    timestamps = [s.timestamp for s in sorted_snaps]
    spreads = [s.yes_ask - s.yes_bid for s in sorted_snaps]

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(timestamps, spreads, "purple", linewidth=1)
    ax.fill_between(timestamps, spreads, alpha=0.2, color="purple")

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())

    ax.set_xlabel("Date")
    ax.set_ylabel("Spread (cents)")
    ax.set_title(title or f"Bid-Ask Spread: {ticker}")
    ax.grid(True, alpha=0.3)

    plt.xticks(rotation=45)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_volume_profile(
    profile: "VolumeProfile",
    title: str | None = None,
    save_path: Path | str | None = None,
) -> Figure:
    """
    Plot volume distribution by hour of day.

    Args:
        profile: VolumeProfile from MarketMetrics
        title: Chart title
        save_path: Optional path to save figure

    Returns:
        Matplotlib Figure
    """
    from kalshi_research.analysis.metrics import VolumeProfile as VP

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Hourly volume
    hours = list(range(24))
    volumes = [profile.hourly_volume.get(h, 0) for h in hours]

    ax1.bar(hours, volumes, color="steelblue", edgecolor="black", alpha=0.7)
    ax1.set_xlabel("Hour (UTC)")
    ax1.set_ylabel("Average Volume")
    ax1.set_title("Volume by Hour")
    ax1.set_xticks(hours[::2])
    ax1.grid(True, alpha=0.3, axis="y")

    # Daily volume
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    day_volumes = [profile.daily_volume.get(d, 0) for d in days]

    ax2.bar(days, day_volumes, color="coral", edgecolor="black", alpha=0.7)
    ax2.set_xlabel("Day of Week")
    ax2.set_ylabel("Average Volume")
    ax2.set_title("Volume by Day")
    ax2.grid(True, alpha=0.3, axis="y")

    fig.suptitle(title or f"Volume Profile: {profile.ticker}")
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig
```

### 3.4 CLI Integration

```python
# Add to cli.py

@data_app.command("chart")
def generate_chart(
    ticker: Annotated[str, typer.Argument(help="Market ticker")],
    chart_type: Annotated[str, typer.Option("--type", "-t", help="Chart type: timeline, spread, volume")] = "timeline",
    output: Annotated[str, typer.Option("--output", "-o", help="Output file path")] = "",
    days: Annotated[int, typer.Option("--days", "-d", help="Days of history")] = 30,
) -> None:
    """Generate charts for a market."""
    ...


@data_app.command("metrics")
def show_metrics(
    ticker: Annotated[str, typer.Argument(help="Market ticker")],
) -> None:
    """Show market efficiency metrics."""
    ...
```

---

## 4. Implementation Tasks

### 4.1 Phase 1: Metrics Module

- [ ] Implement `SpreadStats`, `VolatilityStats`, `VolumeProfile` dataclasses
- [ ] Implement `MarketMetrics.compute_spread_stats()`
- [ ] Implement `MarketMetrics.compute_volatility()`
- [ ] Implement `MarketMetrics.compute_volume_profile()`
- [ ] Write unit tests for all metrics

### 4.2 Phase 2: Visualization Module

- [ ] Implement `plot_calibration_curve()`
- [ ] Implement `plot_probability_timeline()`
- [ ] Implement `plot_edge_histogram()`
- [ ] Implement `plot_spread_timeline()`
- [ ] Implement `plot_volume_profile()`
- [ ] Write visual tests (save reference images)

### 4.3 Phase 3: CLI Integration

- [ ] Add `kalshi data chart` command
- [ ] Add `kalshi data metrics` command
- [ ] Add chart export to PNG/SVG

---

## 5. Acceptance Criteria

1. **Metrics**: All 3 metric types compute correctly
2. **Volatility**: Handles edge cases (zero prices, sparse data)
3. **Charts**: All 5 chart types render without errors
4. **Export**: Charts save to file at 150 DPI
5. **CLI**: Commands generate charts for any ticker
6. **Tests**: >85% coverage on metrics and visualization

---

## 6. Usage Examples

```python
# Metrics usage
from kalshi_research.analysis.metrics import MarketMetrics

metrics = MarketMetrics()

# Compute spread stats
spread = metrics.compute_spread_stats(market, snapshots)
print(f"Current spread: {spread.current_spread}c")
print(f"Avg spread: {spread.avg_spread:.1f}c")
print(f"Relative spread: {spread.relative_spread:.2%}")

# Compute volatility
vol = metrics.compute_volatility(snapshots)
print(f"Daily volatility: {vol.daily_volatility:.1%}")
print(f"Max daily move: {vol.max_daily_move:.1%}")
```

```python
# Visualization usage
from kalshi_research.analysis.visualization import (
    plot_calibration_curve,
    plot_probability_timeline,
)

# Plot calibration
result = analyzer.compute_calibration(forecasts, outcomes)
fig = plot_calibration_curve(result, save_path="charts/calibration.png")

# Plot timeline
fig = plot_probability_timeline(snapshots, save_path="charts/btc_timeline.png")
plt.show()
```

```bash
# CLI usage
kalshi data chart KXBTC-25JAN-T100000 --type timeline --days 30 --output btc.png
kalshi data chart KXBTC-25JAN-T100000 --type spread --days 7
kalshi data metrics KXBTC-25JAN-T100000
```

---

## 7. Future Considerations

- Interactive Plotly charts for notebooks
- Candlestick charts with volume
- Multiple markets on same chart (overlay)
- Annotation support (mark events, settlements)
- Custom color themes
- Export to HTML dashboards
- Real-time updating charts (streaming)
