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

### 2.2 Edge Detection

An "edge" exists when:
1. Your probability estimate differs significantly from market price
2. Historical patterns suggest mispricing
3. Related markets show inconsistent pricing

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
import numpy as np


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

    # Brier decomposition
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

    def __init__(self, n_bins: int = 10) -> None:
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
            Brier score (lower is better, 0 = perfect)
        """
        forecasts = np.asarray(forecasts)
        outcomes = np.asarray(outcomes)
        return float(np.mean((forecasts - outcomes) ** 2))

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
        forecasts = np.asarray(forecasts)
        outcomes = np.asarray(outcomes)
        n = len(forecasts)
        base_rate = np.mean(outcomes)

        # Brier score
        brier = self.compute_brier_score(forecasts, outcomes)

        # Climatology baseline (always predict base rate)
        climatology_brier = base_rate * (1 - base_rate)
        skill_score = 1 - (brier / climatology_brier) if climatology_brier > 0 else 0.0

        # Bin forecasts for calibration curve
        bin_edges = np.linspace(0, 1, self.n_bins + 1)
        bin_indices = np.digitize(forecasts, bin_edges[1:-1])

        predicted_probs = np.full(self.n_bins, np.nan)
        actual_freqs = np.full(self.n_bins, np.nan)
        bin_counts = np.zeros(self.n_bins, dtype=int)

        for i in range(self.n_bins):
            mask = bin_indices == i
            count = np.sum(mask)
            bin_counts[i] = count

            if count > 0:
                predicted_probs[i] = np.mean(forecasts[mask])
                actual_freqs[i] = np.mean(outcomes[mask])

        # Brier decomposition
        reliability = 0.0
        resolution = 0.0
        for i in range(self.n_bins):
            if bin_counts[i] > 0:
                reliability += bin_counts[i] * (actual_freqs[i] - predicted_probs[i]) ** 2
                resolution += bin_counts[i] * (actual_freqs[i] - base_rate) ** 2
        reliability /= n
        resolution /= n

        uncertainty = base_rate * (1 - base_rate)

        return CalibrationResult(
            brier_score=brier,
            brier_skill_score=float(skill_score),
            n_samples=n,
            bins=bin_edges,
            predicted_probs=predicted_probs,
            actual_freqs=actual_freqs,
            bin_counts=bin_counts,
            reliability=reliability,
            resolution=resolution,
            uncertainty=uncertainty,
        )
```

### 3.3 Edge Detection Module

```python
# src/kalshi_research/analysis/edge.py
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EdgeType(str, Enum):
    THESIS = "thesis"           # Your view differs from market
    VOLATILITY = "volatility"   # Unusual price movement
    SPREAD = "spread"           # Wide spread opportunity
    VOLUME = "volume"           # Volume spike
    CORRELATION = "correlation"  # Related market inconsistency


@dataclass
class Edge:
    """Represents a potential trading edge."""

    ticker: str
    edge_type: EdgeType
    confidence: float          # 0-1 confidence in edge
    market_price: float        # Current market probability
    your_estimate: float | None  # Your probability estimate
    expected_value: float | None  # Expected profit per contract (cents)

    description: str
    detected_at: datetime

    # Supporting data (mypy strict requires parameterized dict)
    metadata: dict[str, Any]

    def __str__(self) -> str:
        yours = f"{self.your_estimate:.0%}" if self.your_estimate is not None else "N/A"
        ev = f"{self.expected_value:+.1f}c" if self.expected_value is not None else "N/A"
        return (
            f"[{self.edge_type.value.upper()}] {self.ticker}\n"
            f"  Market: {self.market_price:.0%} | Yours: {yours} | EV: {ev}\n"
            f"  {self.description}"
        )


class EdgeDetector:
    """Detect potential trading edges in market data."""

    def __init__(
        self,
        min_spread_cents: int = 5,
        min_volume_spike: float = 3.0,
        min_price_move: float = 0.10,
    ) -> None:
        self.min_spread_cents = min_spread_cents
        self.min_volume_spike = min_volume_spike
        self.min_price_move = min_price_move

    def detect_thesis_edge(
        self,
        ticker: str,
        market_prob: float,
        your_prob: float,
        min_edge: float = 0.05,
    ) -> Edge | None:
        """
        Detect edge when your estimate differs from market.
        
        Args:
            ticker: Market ticker
            market_prob: Current market probability (0-1)
            your_prob: Your probability estimate (0-1)
            min_edge: Minimum difference to flag (default 5%)
        """
        diff = your_prob - market_prob

        if abs(diff) < min_edge:
            return None

        # Calculate Expected Value (EV) in cents
        # EV = (Prob_Win * Profit) - (Prob_Loss * Risk)
        # Note: Using float for stats analysis, Decimal preferred for execution.
        if diff > 0:
            # Buy YES: Cost = market_prob * 100
            cost = market_prob * 100
            # If win (p=your_prob), profit = 100 - cost. If lose, loss = cost.
            ev = (your_prob * (100 - cost)) - ((1 - your_prob) * cost)
            side = "YES"
        else:
            # Buy NO: Cost = (1 - market_prob) * 100
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
            detected_at=datetime.now(timezone.utc),
            metadata={"side": side, "diff": diff},
        )

    def detect_spread_edge(
        self,
        ticker: str,
        bid: int,
        ask: int,
        typical_spread: int = 2,
    ) -> Edge | None:
        """Detect unusually wide spreads."""
        spread = ask - bid

        if spread <= self.min_spread_cents:
            return None

        # Wide spread might indicate opportunity or illiquidity
        return Edge(
            ticker=ticker,
            edge_type=EdgeType.SPREAD,
            confidence=min((spread - typical_spread) / 10, 1.0),
            market_price=(bid + ask) / 200.0,
            your_estimate=None,
            expected_value=float(spread / 2),  # Potential capture
            description=f"Wide spread: {spread}c (typical: {typical_spread}c)",
            detected_at=datetime.now(timezone.utc),
            metadata={"bid": bid, "ask": ask, "spread": spread},
        )
    
    # ... other detectors ...
```

### 3.4 Market Scanner

Same as previous draft, but ensure usage of `datetime.now(timezone.utc)` where appropriate.

### 3.5 Research Thesis Framework

```python
# src/kalshi_research/research/thesis.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ThesisStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    RESOLVED = "resolved"
    ABANDONED = "abandoned"


@dataclass
class Thesis:
    """
    A research thesis about a market or set of markets.
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
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None
    actual_outcome: str | None = None  # yes, no, void

    # Notes over time (mypy strict requires parameterized dict)
    updates: list[dict[str, Any]] = field(default_factory=list)

    def add_update(self, note: str) -> None:
        """Add a timestamped update to the thesis."""
        self.updates.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": note,
        })

    def resolve(self, outcome: str) -> None:
        """Mark thesis as resolved with outcome."""
        self.status = ThesisStatus.RESOLVED
        self.resolved_at = datetime.now(timezone.utc)
        self.actual_outcome = outcome

    @property
    def edge_size(self) -> float:
        """Difference between your estimate and market."""
        return self.your_probability - self.market_probability

    @property
    def was_correct(self) -> bool | None:
        """Did your thesis predict correctly?"""
        if self.actual_outcome is None:
            return None

        if self.actual_outcome == "yes":
            return self.your_probability > 0.5
        elif self.actual_outcome == "no":
            return self.your_probability < 0.5
        return None
```

### 3.6 Visualization Helpers

Standard matplotlib implementation. No changes needed other than standard library usage.

---

## 4. Implementation Tasks

### 4.1 Phase 1: Calibration

- [ ] Implement Brier score calculation
- [ ] Implement calibration curve computation
- [ ] Add Brier decomposition (reliability, resolution)
- [ ] Write unit tests with synthetic data
- [ ] Create calibration analysis notebook

### 4.2 Phase 2: Edge Detection

- [ ] Implement thesis edge detection (fix UTC timestamps)
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

- [ ] Implement Thesis dataclass (UTC aware)
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
4. **Thesis Tracking**: Persists and loads theses correctly using UTC
5. **Visualization**: All plots render correctly in Jupyter
6. **Tests**: >85% coverage on analysis modules

---

## 6. Usage Examples

```python
# Example: Calibration analysis
import asyncio
import numpy as np
from kalshi_research.analysis.calibration import CalibrationAnalyzer

# Synthetic example data
forecasts = np.array([0.7, 0.3, 0.8, 0.5, 0.9, 0.2, 0.6, 0.4])
outcomes = np.array([1, 0, 1, 1, 1, 0, 0, 1])

analyzer = CalibrationAnalyzer(n_bins=5)
result = analyzer.compute_calibration(forecasts, outcomes)
print(result)
# Output:
# Calibration Results (n=8):
#   Brier Score: 0.1550
#   Skill Score: 0.3800
#   Reliability: 0.0250
#   Resolution:  0.1000
```

```python
# Example: Edge detection
from kalshi_research.analysis.edge import EdgeDetector

detector = EdgeDetector()

# You think market is underpriced
edge = detector.detect_thesis_edge(
    ticker="KXBTC-25JAN-T100000",
    market_prob=0.35,  # Market says 35%
    your_prob=0.55,    # You think 55%
)

if edge:
    print(edge)
    # Output:
    # [THESIS] KXBTC-25JAN-T100000
    #   Market: 35% | Yours: 55% | EV: +20.0c
    #   Buy YES: You estimate 55% vs market 35%
```

---

## 7. Future Considerations

- Add machine learning for pattern detection
- Implement news sentiment analysis integration
- Add correlation analysis between related markets
- Build alert system for edge detection triggers
- Create backtesting framework for thesis validation
- Add portfolio-level analytics (Kelly criterion sizing)
