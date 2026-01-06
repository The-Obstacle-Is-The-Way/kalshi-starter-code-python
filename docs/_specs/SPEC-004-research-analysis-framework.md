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

(Same as previous draft, using standard `numpy`/`scipy`)

### 3.3 Edge Detection Module

```python
# src/kalshi_research/analysis/edge.py
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from decimal import Decimal
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
    expected_value: Optional[float]  # Expected profit per contract (cents)

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
    resolved_at: Optional[datetime] = None
    actual_outcome: Optional[str] = None  # yes, no, void

    # Notes over time
    updates: list[dict] = field(default_factory=list)

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
    def was_correct(self) -> Optional[bool]:
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

```