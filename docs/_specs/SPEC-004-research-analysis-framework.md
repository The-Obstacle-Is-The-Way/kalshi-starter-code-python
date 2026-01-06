# SPEC-004: Research & Analysis Framework

**Status:** Draft
**Priority:** P1 (Core value proposition)
**Estimated Complexity:** High
**Dependencies:** SPEC-001, SPEC-002, SPEC-003

---

## 1. Overview

Build the analytical tools that transform raw Kalshi market data into actionable research insights: calibration analysis, edge detection, probability tracking, and market scanning.

### 1.1 Goals

- Market scanner to find interesting opportunities
- Calibration scoring (how accurate are prediction markets?)
- Edge detection (flag potential mispricing)
- Probability tracking over time
- Event correlation analysis
- Research thesis testing framework

### 1.2 Non-Goals

- Automated trading signals
- Real-time alerting infrastructure
- Machine learning price prediction
- Portfolio optimization

---

## 2. Core Analysis Concepts

### 2.1 Calibration Analysis

**What is calibration?**
A perfectly calibrated forecaster assigns probabilities that match actual frequencies. If a market prices an event at 70%, and we look at all markets priced at 70%, exactly 70% should resolve YES.

**Brier Score:**
```
Brier Score = (1/N) * Σ(forecast - outcome)²
```
- Range: 0 (perfect) to 1 (worst)
- Outcome: 1 if YES, 0 if NO
- Lower is better

**Calibration Curve:**
Plot predicted probability (x-axis) vs actual frequency (y-axis). Perfect calibration = 45° line.

### 2.2 Edge Detection

An "edge" exists when:
1. Your probability estimate differs significantly from market price
2. Historical patterns suggest mispricing
3. Related markets show inconsistent pricing

**Types of edges:**
- **Thesis edge**: You believe probability differs from market
- **Arbitrage edge**: Related markets don't add up
- **Timing edge**: Market hasn't reacted to news yet
- **Liquidity edge**: Wide spreads allow profitable entry

### 2.3 Market Efficiency Metrics

- **Spread**: Ask - Bid (cost of immediacy)
- **Depth**: Volume available at best prices
- **Volatility**: Price movement magnitude
- **Volume Profile**: When does trading happen?

---

## 3. Technical Specification

### 3.1 Module Structure

```
src/kalshi_research/
├── analysis/
│   ├── __init__.py
│   ├── calibration.py      # Brier scores, calibration curves
│   ├── edge.py             # Edge detection algorithms
│   ├── scanner.py          # Market opportunity scanner
│   ├── correlation.py      # Event correlation analysis
│   ├── metrics.py          # Market efficiency metrics
│   └── visualization.py    # Chart generation
├── research/
│   ├── __init__.py
│   ├── thesis.py           # Thesis testing framework
│   ├── backtest.py         # Historical thesis testing
│   └── notebook_utils.py   # Jupyter helpers
notebooks/
├── 01_exploration.ipynb    # Initial data exploration
├── 02_calibration.ipynb    # Calibration analysis
├── 03_edge_detection.ipynb # Finding opportunities
└── templates/
    └── market_analysis.ipynb
```

### 3.2 Calibration Module

```python
# src/kalshi_research/analysis/calibration.py
from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class CalibrationResult:
    """Results from calibration analysis."""

    brier_score: float
    brier_skill_score: float  # vs climatology baseline
    n_samples: int

    # Calibration curve data
    bins: np.ndarray           # Probability bins (e.g., [0.1, 0.2, ...])
    predicted_probs: np.ndarray  # Mean predicted prob per bin
    actual_freqs: np.ndarray     # Actual YES frequency per bin
    bin_counts: np.ndarray       # Samples per bin

    # Resolution and reliability decomposition
    reliability: float         # Calibration error component
    resolution: float          # Discrimination ability
    uncertainty: float         # Base rate uncertainty

    def __str__(self) -> str:
        return (
            f"Calibration Results (n={self.n_samples}):\n"
            f"  Brier Score: {self.brier_score:.4f}\n"
            f"  Skill Score: {self.brier_skill_score:.4f}\n"
            f"  Reliability: {self.reliability:.4f}\n"
            f"  Resolution:  {self.resolution:.4f}"
        )


class CalibrationAnalyzer:
    """Analyze prediction market calibration."""

    def __init__(self, n_bins: int = 10):
        self.n_bins = n_bins

    def compute_brier_score(
        self,
        forecasts: np.ndarray,
        outcomes: np.ndarray,
    ) -> float:
        """
        Compute Brier score for forecasts.

        Args:
            forecasts: Predicted probabilities (0-1)
            outcomes: Actual outcomes (0 or 1)

        Returns:
            Brier score (lower is better)
        """
        return np.mean((forecasts - outcomes) ** 2)

    def compute_calibration(
        self,
        forecasts: np.ndarray,
        outcomes: np.ndarray,
    ) -> CalibrationResult:
        """
        Full calibration analysis with Brier decomposition.

        Args:
            forecasts: Predicted probabilities (0-1)
            outcomes: Actual outcomes (0 or 1)

        Returns:
            CalibrationResult with all metrics
        """
        n = len(forecasts)
        base_rate = np.mean(outcomes)

        # Brier score
        brier = self.compute_brier_score(forecasts, outcomes)

        # Climatology baseline (always predict base rate)
        climatology_brier = base_rate * (1 - base_rate)
        skill_score = 1 - (brier / climatology_brier) if climatology_brier > 0 else 0

        # Bin forecasts for calibration curve
        bin_edges = np.linspace(0, 1, self.n_bins + 1)
        bin_indices = np.digitize(forecasts, bin_edges[1:-1])

        predicted_probs = []
        actual_freqs = []
        bin_counts = []

        for i in range(self.n_bins):
            mask = bin_indices == i
            count = np.sum(mask)
            bin_counts.append(count)

            if count > 0:
                predicted_probs.append(np.mean(forecasts[mask]))
                actual_freqs.append(np.mean(outcomes[mask]))
            else:
                predicted_probs.append(np.nan)
                actual_freqs.append(np.nan)

        # Brier decomposition
        # Reliability (calibration error)
        reliability = 0
        for i in range(self.n_bins):
            if bin_counts[i] > 0:
                reliability += bin_counts[i] * (actual_freqs[i] - predicted_probs[i]) ** 2
        reliability /= n

        # Resolution (discrimination)
        resolution = 0
        for i in range(self.n_bins):
            if bin_counts[i] > 0:
                resolution += bin_counts[i] * (actual_freqs[i] - base_rate) ** 2
        resolution /= n

        # Uncertainty
        uncertainty = base_rate * (1 - base_rate)

        return CalibrationResult(
            brier_score=brier,
            brier_skill_score=skill_score,
            n_samples=n,
            bins=bin_edges,
            predicted_probs=np.array(predicted_probs),
            actual_freqs=np.array(actual_freqs),
            bin_counts=np.array(bin_counts),
            reliability=reliability,
            resolution=resolution,
            uncertainty=uncertainty,
        )

    async def analyze_market_calibration(
        self,
        settlements: list,  # List of (ticker, final_prob, outcome)
        time_before_settlement: int = 3600,  # Seconds before
    ) -> CalibrationResult:
        """
        Analyze calibration using market prices before settlement.

        Args:
            settlements: List of settled markets with outcomes
            time_before_settlement: How long before settlement to measure

        Returns:
            CalibrationResult
        """
        forecasts = []
        outcomes = []

        for ticker, final_prob, outcome in settlements:
            forecasts.append(final_prob)
            outcomes.append(1 if outcome == "yes" else 0)

        return self.compute_calibration(
            np.array(forecasts),
            np.array(outcomes),
        )

    def analyze_by_category(
        self,
        data: pd.DataFrame,  # ticker, forecast, outcome, category
    ) -> dict[str, CalibrationResult]:
        """Compute calibration separately by category."""
        results = {}
        for category in data["category"].unique():
            subset = data[data["category"] == category]
            results[category] = self.compute_calibration(
                subset["forecast"].values,
                subset["outcome"].values,
            )
        return results
```

### 3.3 Edge Detection Module

```python
# src/kalshi_research/analysis/edge.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum
import numpy as np


class EdgeType(str, Enum):
    THESIS = "thesis"           # Your view differs from market
    VOLATILITY = "volatility"   # Unusual price movement
    SPREAD = "spread"           # Wide spread opportunity
    VOLUME = "volume"           # Volume spike
    CORRELATION = "correlation" # Related market inconsistency


@dataclass
class Edge:
    """Represents a potential trading edge."""

    ticker: str
    edge_type: EdgeType
    confidence: float          # 0-1 confidence in edge
    market_price: float        # Current market probability
    your_estimate: Optional[float]  # Your probability estimate
    expected_value: Optional[float]  # Expected profit per contract

    description: str
    detected_at: datetime

    # Supporting data
    metadata: dict

    def __str__(self) -> str:
        return (
            f"[{self.edge_type.value.upper()}] {self.ticker}\n"
            f"  Market: {self.market_price:.0%} | "
            f"Yours: {self.your_estimate:.0%} | "
            f"EV: {self.expected_value:+.1f}c\n"
            f"  {self.description}"
        )


class EdgeDetector:
    """Detect potential trading edges in market data."""

    def __init__(
        self,
        min_spread_cents: int = 5,
        min_volume_spike: float = 3.0,
        min_price_move: float = 0.10,
    ):
        self.min_spread_cents = min_spread_cents
        self.min_volume_spike = min_volume_spike
        self.min_price_move = min_price_move

    def detect_thesis_edge(
        self,
        ticker: str,
        market_prob: float,
        your_prob: float,
        min_edge: float = 0.05,
    ) -> Optional[Edge]:
        """
        Detect edge when your estimate differs from market.

        Args:
            ticker: Market ticker
            market_prob: Current market probability (0-1)
            your_prob: Your probability estimate (0-1)
            min_edge: Minimum difference to flag (default 5%)

        Returns:
            Edge if significant difference, None otherwise
        """
        diff = your_prob - market_prob

        if abs(diff) < min_edge:
            return None

        # Calculate expected value
        # If you think prob is higher, buy YES
        # EV = (your_prob * (100 - market_price)) - ((1 - your_prob) * market_price)
        if diff > 0:
            # Buy YES at ask
            cost = market_prob * 100  # Approximate
            ev = (your_prob * (100 - cost)) - ((1 - your_prob) * cost)
            side = "YES"
        else:
            # Buy NO (or sell YES)
            cost = (1 - market_prob) * 100
            ev = ((1 - your_prob) * (100 - cost)) - (your_prob * cost)
            side = "NO"

        return Edge(
            ticker=ticker,
            edge_type=EdgeType.THESIS,
            confidence=min(abs(diff) / 0.20, 1.0),  # Scale to 20% max
            market_price=market_prob,
            your_estimate=your_prob,
            expected_value=ev,
            description=f"Buy {side}: You estimate {your_prob:.0%} vs market {market_prob:.0%}",
            detected_at=datetime.utcnow(),
            metadata={"side": side, "diff": diff},
        )

    def detect_spread_edge(
        self,
        ticker: str,
        bid: int,
        ask: int,
        typical_spread: int = 2,
    ) -> Optional[Edge]:
        """Detect unusually wide spreads."""
        spread = ask - bid

        if spread <= self.min_spread_cents:
            return None

        # Wide spread might indicate opportunity or illiquidity
        return Edge(
            ticker=ticker,
            edge_type=EdgeType.SPREAD,
            confidence=min((spread - typical_spread) / 10, 1.0),
            market_price=(bid + ask) / 200,  # Midpoint as prob
            your_estimate=None,
            expected_value=spread / 2,  # Potential capture
            description=f"Wide spread: {spread}c (typical: {typical_spread}c)",
            detected_at=datetime.utcnow(),
            metadata={"bid": bid, "ask": ask, "spread": spread},
        )

    def detect_volatility_edge(
        self,
        ticker: str,
        current_price: float,
        prices_24h: list[float],
    ) -> Optional[Edge]:
        """Detect unusual price movements."""
        if len(prices_24h) < 10:
            return None

        prices = np.array(prices_24h)
        mean_price = np.mean(prices)
        std_price = np.std(prices)

        if std_price == 0:
            return None

        z_score = (current_price - mean_price) / std_price

        if abs(z_score) < 2:  # Within 2 std devs
            return None

        direction = "UP" if z_score > 0 else "DOWN"
        move_pct = (current_price - mean_price) / mean_price * 100

        return Edge(
            ticker=ticker,
            edge_type=EdgeType.VOLATILITY,
            confidence=min(abs(z_score) / 4, 1.0),
            market_price=current_price,
            your_estimate=None,
            expected_value=None,
            description=f"Price moved {direction} {abs(move_pct):.1f}% ({z_score:.1f}σ)",
            detected_at=datetime.utcnow(),
            metadata={
                "z_score": z_score,
                "mean_24h": mean_price,
                "std_24h": std_price,
            },
        )

    async def scan_all_markets(
        self,
        markets: list,  # List of Market objects with price data
        your_estimates: Optional[dict[str, float]] = None,
    ) -> list[Edge]:
        """
        Scan all markets for potential edges.

        Args:
            markets: List of market data
            your_estimates: Optional dict of ticker -> your probability

        Returns:
            List of detected edges
        """
        edges = []
        your_estimates = your_estimates or {}

        for market in markets:
            # Check thesis edge if you have an estimate
            if market.ticker in your_estimates:
                edge = self.detect_thesis_edge(
                    market.ticker,
                    market.midpoint / 100,
                    your_estimates[market.ticker],
                )
                if edge:
                    edges.append(edge)

            # Check spread
            edge = self.detect_spread_edge(
                market.ticker,
                market.yes_bid,
                market.yes_ask,
            )
            if edge:
                edges.append(edge)

        return edges
```

### 3.4 Market Scanner

```python
# src/kalshi_research/analysis/scanner.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class ScanFilter(str, Enum):
    HIGH_VOLUME = "high_volume"
    LOW_LIQUIDITY = "low_liquidity"
    NEAR_EXPIRY = "near_expiry"
    WIDE_SPREAD = "wide_spread"
    PRICE_MOVERS = "price_movers"
    CLOSE_RACES = "close_races"  # Near 50%


@dataclass
class ScanResult:
    """Result from market scan."""

    ticker: str
    title: str
    filter_matched: ScanFilter
    score: float  # Relevance score
    metrics: dict
    url: str


class MarketScanner:
    """Scan markets for interesting opportunities."""

    BASE_URL = "https://kalshi.com/markets"

    def __init__(self, price_repo, market_repo):
        self.price_repo = price_repo
        self.market_repo = market_repo

    async def scan(
        self,
        filters: list[ScanFilter],
        limit: int = 20,
    ) -> list[ScanResult]:
        """
        Scan markets based on filters.

        Args:
            filters: Which filters to apply
            limit: Max results per filter

        Returns:
            List of matching markets
        """
        results = []

        for filter_type in filters:
            if filter_type == ScanFilter.HIGH_VOLUME:
                results.extend(await self._scan_high_volume(limit))
            elif filter_type == ScanFilter.WIDE_SPREAD:
                results.extend(await self._scan_wide_spread(limit))
            elif filter_type == ScanFilter.CLOSE_RACES:
                results.extend(await self._scan_close_races(limit))
            elif filter_type == ScanFilter.PRICE_MOVERS:
                results.extend(await self._scan_price_movers(limit))

        # Sort by score and dedupe
        seen = set()
        unique = []
        for r in sorted(results, key=lambda x: x.score, reverse=True):
            if r.ticker not in seen:
                seen.add(r.ticker)
                unique.append(r)

        return unique[:limit]

    async def _scan_high_volume(self, limit: int) -> list[ScanResult]:
        """Find markets with highest 24h volume."""
        markets = await self.market_repo.get_by_volume(limit=limit)

        return [
            ScanResult(
                ticker=m.ticker,
                title=m.title,
                filter_matched=ScanFilter.HIGH_VOLUME,
                score=m.volume_24h / 100000,  # Normalize
                metrics={
                    "volume_24h": m.volume_24h,
                    "open_interest": m.open_interest,
                },
                url=f"{self.BASE_URL}/{m.ticker}",
            )
            for m in markets
        ]

    async def _scan_wide_spread(self, limit: int) -> list[ScanResult]:
        """Find markets with unusually wide spreads."""
        markets = await self.market_repo.get_open_markets()

        wide_spread = [
            (m, m.yes_ask - m.yes_bid)
            for m in markets
            if m.yes_ask - m.yes_bid >= 5
        ]
        wide_spread.sort(key=lambda x: x[1], reverse=True)

        return [
            ScanResult(
                ticker=m.ticker,
                title=m.title,
                filter_matched=ScanFilter.WIDE_SPREAD,
                score=spread / 20,
                metrics={
                    "bid": m.yes_bid,
                    "ask": m.yes_ask,
                    "spread": spread,
                },
                url=f"{self.BASE_URL}/{m.ticker}",
            )
            for m, spread in wide_spread[:limit]
        ]

    async def _scan_close_races(self, limit: int) -> list[ScanResult]:
        """Find markets near 50% (uncertain outcomes)."""
        markets = await self.market_repo.get_open_markets()

        close_races = [
            (m, abs(50 - (m.yes_bid + m.yes_ask) / 2))
            for m in markets
            if m.volume_24h > 1000  # Has some activity
        ]
        close_races.sort(key=lambda x: x[1])  # Closest to 50 first

        return [
            ScanResult(
                ticker=m.ticker,
                title=m.title,
                filter_matched=ScanFilter.CLOSE_RACES,
                score=1 - (distance / 50),
                metrics={
                    "midpoint": (m.yes_bid + m.yes_ask) / 2,
                    "distance_from_50": distance,
                },
                url=f"{self.BASE_URL}/{m.ticker}",
            )
            for m, distance in close_races[:limit]
        ]

    async def _scan_price_movers(
        self,
        limit: int,
        hours: int = 24,
        min_move: int = 5,
    ) -> list[ScanResult]:
        """Find markets with significant recent price movement."""
        movers = await self.price_repo.get_markets_by_price_change(
            hours=hours,
            min_change_cents=min_move,
        )

        return [
            ScanResult(
                ticker=m["ticker"],
                title="",  # Would need to join
                filter_matched=ScanFilter.PRICE_MOVERS,
                score=abs(m["change"]) / 20,
                metrics={
                    "current_price": m["current_mid"],
                    "previous_price": m["past_mid"],
                    "change": m["change"],
                },
                url=f"{self.BASE_URL}/{m['ticker']}",
            )
            for m in movers[:limit]
        ]
```

### 3.5 Research Thesis Framework

```python
# src/kalshi_research/research/thesis.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum
import json


class ThesisStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    RESOLVED = "resolved"
    ABANDONED = "abandoned"


@dataclass
class Thesis:
    """
    A research thesis about a market or set of markets.

    Use this to document your reasoning BEFORE placing bets.
    """

    id: str
    title: str
    market_tickers: list[str]

    # Your predictions
    your_probability: float  # 0-1
    market_probability: float  # At time of thesis
    confidence: float  # How sure are you? 0-1

    # Reasoning
    bull_case: str  # Why it might be YES
    bear_case: str  # Why it might be NO
    key_assumptions: list[str]
    invalidation_criteria: list[str]  # What would prove you wrong?

    # Tracking
    status: ThesisStatus = ThesisStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    actual_outcome: Optional[str] = None  # yes, no, void

    # Notes over time
    updates: list[dict] = field(default_factory=list)

    def add_update(self, note: str) -> None:
        """Add a timestamped update to the thesis."""
        self.updates.append({
            "timestamp": datetime.utcnow().isoformat(),
            "note": note,
        })

    def resolve(self, outcome: str) -> None:
        """Mark thesis as resolved with outcome."""
        self.status = ThesisStatus.RESOLVED
        self.resolved_at = datetime.utcnow()
        self.actual_outcome = outcome

    @property
    def edge_size(self) -> float:
        """Difference between your estimate and market."""
        return self.your_probability - self.market_probability

    @property
    def was_correct(self) -> Optional[bool]:
        """Did your thesis predict correctly?"""
        if self.actual_outcome is None:
            return None

        if self.actual_outcome == "yes":
            return self.your_probability > 0.5
        elif self.actual_outcome == "no":
            return self.your_probability < 0.5
        return None

    def to_dict(self) -> dict:
        """Serialize for storage."""
        return {
            "id": self.id,
            "title": self.title,
            "market_tickers": self.market_tickers,
            "your_probability": self.your_probability,
            "market_probability": self.market_probability,
            "confidence": self.confidence,
            "bull_case": self.bull_case,
            "bear_case": self.bear_case,
            "key_assumptions": self.key_assumptions,
            "invalidation_criteria": self.invalidation_criteria,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "actual_outcome": self.actual_outcome,
            "updates": self.updates,
        }


class ThesisTracker:
    """Track and analyze your research theses over time."""

    def __init__(self, storage_path: str = "data/theses.json"):
        self.storage_path = storage_path
        self.theses: dict[str, Thesis] = {}
        self._load()

    def _load(self) -> None:
        """Load theses from storage."""
        try:
            with open(self.storage_path) as f:
                data = json.load(f)
                # Deserialize...
        except FileNotFoundError:
            pass

    def _save(self) -> None:
        """Persist theses to storage."""
        with open(self.storage_path, "w") as f:
            json.dump(
                {k: v.to_dict() for k, v in self.theses.items()},
                f,
                indent=2,
            )

    def create_thesis(
        self,
        title: str,
        tickers: list[str],
        your_prob: float,
        market_prob: float,
        bull_case: str,
        bear_case: str,
        assumptions: list[str],
        invalidation: list[str],
        confidence: float = 0.5,
    ) -> Thesis:
        """Create and store a new thesis."""
        thesis_id = f"thesis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        thesis = Thesis(
            id=thesis_id,
            title=title,
            market_tickers=tickers,
            your_probability=your_prob,
            market_probability=market_prob,
            confidence=confidence,
            bull_case=bull_case,
            bear_case=bear_case,
            key_assumptions=assumptions,
            invalidation_criteria=invalidation,
        )

        self.theses[thesis_id] = thesis
        self._save()
        return thesis

    def get_active_theses(self) -> list[Thesis]:
        """Get all active theses."""
        return [t for t in self.theses.values() if t.status == ThesisStatus.ACTIVE]

    def get_thesis_performance(self) -> dict:
        """Calculate performance metrics across all resolved theses."""
        resolved = [t for t in self.theses.values() if t.status == ThesisStatus.RESOLVED]

        if not resolved:
            return {"total": 0}

        correct = sum(1 for t in resolved if t.was_correct)
        total_edge = sum(abs(t.edge_size) for t in resolved)

        return {
            "total": len(resolved),
            "correct": correct,
            "accuracy": correct / len(resolved),
            "avg_edge": total_edge / len(resolved),
            "avg_confidence": sum(t.confidence for t in resolved) / len(resolved),
        }
```

### 3.6 Visualization Helpers

```python
# src/kalshi_research/analysis/visualization.py
from typing import Optional
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np


def plot_calibration_curve(
    calibration_result,
    title: str = "Calibration Curve",
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Plot calibration curve showing predicted vs actual probabilities.

    Perfect calibration = 45-degree line.
    """
    fig, ax = plt.subplots(figsize=(8, 8))

    # Perfect calibration line
    ax.plot([0, 1], [0, 1], "k--", label="Perfect calibration", alpha=0.7)

    # Actual calibration
    valid = ~np.isnan(calibration_result.predicted_probs)
    ax.plot(
        calibration_result.predicted_probs[valid],
        calibration_result.actual_freqs[valid],
        "o-",
        label=f"Kalshi (Brier={calibration_result.brier_score:.3f})",
        markersize=8,
    )

    # Shade confidence region
    ax.fill_between([0, 1], [0, 0.9], [0.1, 1], alpha=0.1, color="gray")

    ax.set_xlabel("Predicted Probability", fontsize=12)
    ax.set_ylabel("Actual Frequency", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)

    # Add sample counts as annotations
    for i, (pred, actual, count) in enumerate(zip(
        calibration_result.predicted_probs[valid],
        calibration_result.actual_freqs[valid],
        calibration_result.bin_counts[valid],
    )):
        ax.annotate(
            f"n={count}",
            (pred, actual),
            textcoords="offset points",
            xytext=(5, 5),
            fontsize=8,
        )

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_probability_timeline(
    df: pd.DataFrame,
    ticker: str,
    highlight_events: Optional[list[tuple]] = None,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Plot probability over time for a market.

    Args:
        df: DataFrame with 'time' index and 'implied_prob' column
        ticker: Market ticker for title
        highlight_events: List of (datetime, label) to mark
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # Probability timeline
    ax1.fill_between(
        df.index,
        df["implied_prob"] * 100,
        alpha=0.3,
    )
    ax1.plot(df.index, df["implied_prob"] * 100, linewidth=1.5)

    ax1.set_ylabel("Probability (%)", fontsize=11)
    ax1.set_title(f"Probability Timeline: {ticker}", fontsize=14)
    ax1.set_ylim(0, 100)
    ax1.axhline(y=50, color="gray", linestyle="--", alpha=0.5)
    ax1.grid(True, alpha=0.3)

    # Volume bars
    ax2.bar(df.index, df["volume_24h"], alpha=0.7, width=0.02)
    ax2.set_ylabel("24h Volume", fontsize=11)
    ax2.set_xlabel("Date", fontsize=11)
    ax2.grid(True, alpha=0.3)

    # Format x-axis
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    plt.xticks(rotation=45)

    # Highlight events
    if highlight_events:
        for event_time, label in highlight_events:
            for ax in [ax1, ax2]:
                ax.axvline(x=event_time, color="red", linestyle="--", alpha=0.7)
            ax1.annotate(
                label,
                (event_time, ax1.get_ylim()[1]),
                rotation=90,
                fontsize=9,
            )

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_edge_histogram(
    edges: list,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """Plot distribution of detected edges."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Group by edge type
    edge_types = {}
    for edge in edges:
        t = edge.edge_type.value
        if t not in edge_types:
            edge_types[t] = []
        if edge.expected_value:
            edge_types[t].append(edge.expected_value)

    # Plot histograms
    colors = plt.cm.Set2.colors
    for i, (edge_type, values) in enumerate(edge_types.items()):
        ax.hist(
            values,
            bins=20,
            alpha=0.6,
            label=f"{edge_type} (n={len(values)})",
            color=colors[i % len(colors)],
        )

    ax.set_xlabel("Expected Value (cents)", fontsize=11)
    ax.set_ylabel("Count", fontsize=11)
    ax.set_title("Distribution of Detected Edges", fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig
```

---

## 4. Implementation Tasks

### 4.1 Phase 1: Calibration

- [ ] Implement Brier score calculation
- [ ] Implement calibration curve computation
- [ ] Add Brier decomposition (reliability, resolution)
- [ ] Write unit tests with synthetic data
- [ ] Create calibration analysis notebook

### 4.2 Phase 2: Edge Detection

- [ ] Implement thesis edge detection
- [ ] Implement spread edge detection
- [ ] Implement volatility edge detection
- [ ] Create edge scanning pipeline
- [ ] Write edge detection tests

### 4.3 Phase 3: Market Scanner

- [ ] Implement volume scanner
- [ ] Implement spread scanner
- [ ] Implement close race scanner
- [ ] Implement price mover scanner
- [ ] Create CLI for scanning

### 4.4 Phase 4: Research Framework

- [ ] Implement Thesis dataclass
- [ ] Implement ThesisTracker with persistence
- [ ] Add thesis performance analytics
- [ ] Create thesis management notebook

### 4.5 Phase 5: Visualization

- [ ] Implement calibration curve plotting
- [ ] Implement probability timeline plotting
- [ ] Implement edge histogram
- [ ] Create exploration notebook template

---

## 5. Acceptance Criteria

1. **Calibration**: Can compute Brier score for 1000+ settlements in <1s
2. **Edge Detection**: Scans all markets in <30s
3. **Scanner**: Returns top opportunities across all filters
4. **Thesis Tracking**: Persists and loads theses correctly
5. **Visualization**: All plots render correctly in Jupyter
6. **Tests**: >85% coverage on analysis modules

---

## 6. Example Research Workflow

```python
# In Jupyter notebook
from kalshi_research.api import KalshiPublicClient
from kalshi_research.analysis import (
    CalibrationAnalyzer,
    EdgeDetector,
    MarketScanner,
)
from kalshi_research.research import ThesisTracker

# 1. Scan for interesting markets
scanner = MarketScanner(price_repo, market_repo)
opportunities = await scanner.scan([
    ScanFilter.CLOSE_RACES,
    ScanFilter.PRICE_MOVERS,
])

for opp in opportunities[:10]:
    print(f"{opp.ticker}: {opp.metrics}")

# 2. Check historical calibration
analyzer = CalibrationAnalyzer()
settlements = await get_recent_settlements(days=90)
result = analyzer.compute_calibration(forecasts, outcomes)
print(result)
plot_calibration_curve(result)

# 3. Create a thesis
tracker = ThesisTracker()
thesis = tracker.create_thesis(
    title="Fed will cut rates in March",
    tickers=["FED-25MAR-T25"],
    your_prob=0.65,
    market_prob=0.45,
    bull_case="Inflation cooling faster than expected",
    bear_case="Job market still strong, Fed cautious",
    assumptions=["CPI continues downward trend"],
    invalidation=["Core CPI above 0.4% MoM"],
)

# 4. Detect edges
detector = EdgeDetector()
edge = detector.detect_thesis_edge(
    "FED-25MAR-T25",
    market_prob=0.45,
    your_prob=0.65,
)
print(edge)
```

---

## 7. Future Considerations

- Add machine learning for pattern detection
- Implement news sentiment analysis
- Add correlation analysis between markets
- Build alert system for edge detection
- Create backtesting framework for strategies
