# SPEC-006: Event Correlation Analysis

**Status:** ✅ Implemented
**Priority:** P2 (Explicitly requested: "Event Correlation - How do related markets move together?")
**Estimated Complexity:** Medium
**Dependencies:** SPEC-002 (API Client), SPEC-003 (Data Layer)

---

## Implementation References

- `src/kalshi_research/analysis/correlation.py`
- `src/kalshi_research/cli.py` (`kalshi scan arbitrage`, `kalshi analysis correlation`)

---

## 1. Overview

Implement correlation analysis to understand how related Kalshi markets move together. This helps identify arbitrage opportunities, hedging relationships, and market inefficiencies.

### 1.1 Goals

- Detect correlated market pairs (positive and negative correlation)
- Analyze price movement correlation over time
- Identify arbitrage opportunities between related events
- Find hedging relationships
- Group markets by correlation clusters

### 1.2 Non-Goals

- Real-time correlation trading signals
- Complex multivariate factor models
- Cross-market (Kalshi vs external) correlation
- Causation inference

---

## 2. Core Concepts

### 2.1 Correlation Types

| Type | Description | Example |
|------|-------------|---------|
| **Price Correlation** | Markets that move together | BTC $100k vs BTC $110k |
| **Inverse Correlation** | Markets that move opposite | Trump win vs Biden win |
| **Lead-Lag** | One market predicts another | Early state vs final outcome |
| **Cluster** | Group of related markets | All weather markets |

### 2.2 Correlation Metrics

- **Pearson Correlation**: Linear relationship (-1 to +1)
- **Spearman Rank**: Monotonic relationship (handles non-linear)
- **Rolling Correlation**: Time-windowed correlation

### 2.3 Arbitrage Opportunities

When correlated markets diverge unexpectedly:
- If A and B always move together, but B lags behind A's move
- If inverse markets don't sum to ~100% (minus spread)
- If related markets show inconsistent implied probabilities

---

## 3. Technical Specification

### 3.1 Module Structure

```
src/kalshi_research/
├── analysis/
│   ├── correlation.py     # Core correlation analysis
│   └── ...
```

### 3.2 Correlation Module

```python
# src/kalshi_research/analysis/correlation.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import numpy as np
from scipy import stats

from kalshi_research.api.models import Market
from kalshi_research.data.models import PriceSnapshot


class CorrelationType(str, Enum):
    """Types of correlation relationships."""

    POSITIVE = "positive"       # Move together
    NEGATIVE = "negative"       # Move opposite
    LEAD_LAG = "lead_lag"       # One predicts other
    NONE = "none"               # No relationship


@dataclass
class CorrelationResult:
    """Result of correlation analysis between two markets."""

    ticker_a: str
    ticker_b: str
    correlation_type: CorrelationType

    # Correlation metrics
    pearson: float              # Pearson correlation coefficient
    pearson_pvalue: float       # Statistical significance
    spearman: float             # Spearman rank correlation
    spearman_pvalue: float

    # Time window
    start_time: datetime
    end_time: datetime
    n_samples: int

    # Lead-lag analysis (if applicable)
    lead_lag_days: int = 0      # Positive = A leads B
    lead_lag_correlation: float = 0.0

    def is_significant(self, alpha: float = 0.05) -> bool:
        """Check if correlation is statistically significant."""
        return self.pearson_pvalue < alpha

    @property
    def strength(self) -> str:
        """Describe correlation strength."""
        r = abs(self.pearson)
        if r < 0.3:
            return "weak"
        elif r < 0.7:
            return "moderate"
        else:
            return "strong"


@dataclass
class ArbitrageOpportunity:
    """A potential arbitrage between correlated markets."""

    tickers: list[str]
    opportunity_type: str       # "divergence", "inverse_sum", "cluster_outlier"
    expected_relationship: str  # What we expect
    actual_values: dict[str, float]
    divergence: float           # Size of mispricing
    confidence: float           # 0-1
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CorrelationAnalyzer:
    """
    Analyze correlations between Kalshi markets.

    Usage:
        analyzer = CorrelationAnalyzer(db)
        correlated = await analyzer.find_correlated_markets(markets)
        arb = await analyzer.find_arbitrage_opportunities(markets)
    """

    def __init__(
        self,
        min_samples: int = 30,
        min_correlation: float = 0.5,
        significance_level: float = 0.05,
    ) -> None:
        """
        Initialize correlation analyzer.

        Args:
            min_samples: Minimum data points for analysis
            min_correlation: Minimum |r| to consider correlated
            significance_level: Alpha for hypothesis testing
        """
        self.min_samples = min_samples
        self.min_correlation = min_correlation
        self.significance_level = significance_level

    def compute_correlation(
        self,
        prices_a: np.ndarray,
        prices_b: np.ndarray,
        ticker_a: str,
        ticker_b: str,
        timestamps: list[datetime] | None = None,
    ) -> CorrelationResult | None:
        """
        Compute correlation between two price series.

        Args:
            prices_a: Price series for market A
            prices_b: Price series for market B
            ticker_a: Ticker for market A
            ticker_b: Ticker for market B
            timestamps: Optional timestamps for the series

        Returns:
            CorrelationResult or None if insufficient data
        """
        # Validate inputs
        if len(prices_a) != len(prices_b):
            return None
        if len(prices_a) < self.min_samples:
            return None

        # Remove NaN values
        mask = ~(np.isnan(prices_a) | np.isnan(prices_b))
        a = prices_a[mask]
        b = prices_b[mask]

        if len(a) < self.min_samples:
            return None

        # Compute Pearson correlation
        pearson_r, pearson_p = stats.pearsonr(a, b)

        # Compute Spearman rank correlation
        spearman_r, spearman_p = stats.spearmanr(a, b)

        # Determine correlation type
        if abs(pearson_r) < 0.3:
            corr_type = CorrelationType.NONE
        elif pearson_r > 0:
            corr_type = CorrelationType.POSITIVE
        else:
            corr_type = CorrelationType.NEGATIVE

        # Time bounds
        if timestamps:
            start_time = min(timestamps)
            end_time = max(timestamps)
        else:
            start_time = datetime.now(timezone.utc)
            end_time = datetime.now(timezone.utc)

        return CorrelationResult(
            ticker_a=ticker_a,
            ticker_b=ticker_b,
            correlation_type=corr_type,
            pearson=float(pearson_r),
            pearson_pvalue=float(pearson_p),
            spearman=float(spearman_r),
            spearman_pvalue=float(spearman_p),
            start_time=start_time,
            end_time=end_time,
            n_samples=len(a),
        )

    async def find_correlated_markets(
        self,
        snapshots: dict[str, list[PriceSnapshot]],
        top_n: int = 20,
    ) -> list[CorrelationResult]:
        """
        Find all correlated market pairs.

        Args:
            snapshots: Dict mapping ticker to price snapshots
            top_n: Return top N most correlated pairs

        Returns:
            List of CorrelationResults sorted by |correlation|
        """
        tickers = list(snapshots.keys())
        results: list[CorrelationResult] = []

        # Compare all pairs
        for i, ticker_a in enumerate(tickers):
            for ticker_b in tickers[i + 1:]:
                snaps_a = snapshots[ticker_a]
                snaps_b = snapshots[ticker_b]

                # Align by timestamp
                aligned_a, aligned_b, timestamps = self._align_timeseries(
                    snaps_a, snaps_b
                )

                if len(aligned_a) < self.min_samples:
                    continue

                result = self.compute_correlation(
                    np.array(aligned_a),
                    np.array(aligned_b),
                    ticker_a,
                    ticker_b,
                    timestamps,
                )

                if result and result.is_significant(self.significance_level):
                    if abs(result.pearson) >= self.min_correlation:
                        results.append(result)

        # Sort by absolute correlation
        results.sort(key=lambda r: abs(r.pearson), reverse=True)
        return results[:top_n]

    def find_inverse_markets(
        self,
        markets: list[Market],
        tolerance: float = 0.05,
    ) -> list[tuple[Market, Market, float]]:
        """
        Find market pairs that should sum to ~100% (inverse relationship).

        Common examples:
        - Trump vs Biden (should sum to ~100%)
        - BTC above X vs below X

        Args:
            markets: List of markets to analyze
            tolerance: Allowed deviation from 100%

        Returns:
            List of (market_a, market_b, sum_deviation) tuples
        """
        results: list[tuple[Market, Market, float]] = []

        # Group by event
        by_event: dict[str, list[Market]] = {}
        for m in markets:
            event_ticker = m.event_ticker
            if event_ticker not in by_event:
                by_event[event_ticker] = []
            by_event[event_ticker].append(m)

        # Check pairs within same event
        for event_markets in by_event.values():
            if len(event_markets) == 2:
                m1, m2 = event_markets
                prob_sum = (m1.yes_price + m2.yes_price) / 100.0

                if abs(prob_sum - 1.0) > tolerance:
                    deviation = prob_sum - 1.0
                    results.append((m1, m2, deviation))

        return results

    def find_arbitrage_opportunities(
        self,
        markets: list[Market],
        correlated_pairs: list[CorrelationResult],
        divergence_threshold: float = 0.10,
    ) -> list[ArbitrageOpportunity]:
        """
        Find potential arbitrage from correlated markets diverging.

        Args:
            markets: Current market data
            correlated_pairs: Known correlated pairs
            divergence_threshold: Min divergence to flag

        Returns:
            List of arbitrage opportunities
        """
        opportunities: list[ArbitrageOpportunity] = []
        market_prices = {m.ticker: m.yes_price / 100.0 for m in markets}

        for pair in correlated_pairs:
            if pair.ticker_a not in market_prices:
                continue
            if pair.ticker_b not in market_prices:
                continue

            price_a = market_prices[pair.ticker_a]
            price_b = market_prices[pair.ticker_b]

            # Check for divergence from expected relationship
            if pair.correlation_type == CorrelationType.POSITIVE:
                # Should move together
                divergence = abs(price_a - price_b)
                if divergence > divergence_threshold:
                    opportunities.append(ArbitrageOpportunity(
                        tickers=[pair.ticker_a, pair.ticker_b],
                        opportunity_type="divergence",
                        expected_relationship=f"Move together (r={pair.pearson:.2f})",
                        actual_values={
                            pair.ticker_a: price_a,
                            pair.ticker_b: price_b,
                        },
                        divergence=divergence,
                        confidence=min(abs(pair.pearson), 1.0),
                    ))

            elif pair.correlation_type == CorrelationType.NEGATIVE:
                # Should sum to ~100%
                prob_sum = price_a + price_b
                if abs(prob_sum - 1.0) > divergence_threshold:
                    opportunities.append(ArbitrageOpportunity(
                        tickers=[pair.ticker_a, pair.ticker_b],
                        opportunity_type="inverse_sum",
                        expected_relationship=f"Sum to ~100% (r={pair.pearson:.2f})",
                        actual_values={
                            pair.ticker_a: price_a,
                            pair.ticker_b: price_b,
                            "sum": prob_sum,
                        },
                        divergence=abs(prob_sum - 1.0),
                        confidence=min(abs(pair.pearson), 1.0),
                    ))

        return opportunities

    def _align_timeseries(
        self,
        snaps_a: list[PriceSnapshot],
        snaps_b: list[PriceSnapshot],
    ) -> tuple[list[float], list[float], list[datetime]]:
        """Align two timeseries by timestamp."""
        # Build lookup by rounded timestamp
        lookup_a: dict[str, float] = {}
        for snap in snaps_a:
            # Round to hour for alignment
            key = snap.timestamp.replace(minute=0, second=0, microsecond=0).isoformat()
            lookup_a[key] = snap.yes_price

        aligned_a: list[float] = []
        aligned_b: list[float] = []
        timestamps: list[datetime] = []

        for snap in snaps_b:
            key = snap.timestamp.replace(minute=0, second=0, microsecond=0).isoformat()
            if key in lookup_a:
                aligned_a.append(lookup_a[key])
                aligned_b.append(snap.yes_price)
                timestamps.append(snap.timestamp)

        return aligned_a, aligned_b, timestamps
```

### 3.3 CLI Integration

```python
# Add to cli.py

@data_app.command("correlations")
def analyze_correlations(
    top_n: Annotated[int, typer.Option("--top", "-n", help="Number of top correlations")] = 20,
    min_correlation: Annotated[float, typer.Option("--min-r", help="Minimum correlation")] = 0.5,
) -> None:
    """Analyze correlations between markets."""
    from kalshi_research.analysis.correlation import CorrelationAnalyzer
    ...


@data_app.command("arbitrage")
def find_arbitrage() -> None:
    """Find potential arbitrage opportunities from market divergence."""
    ...
```

---

## 4. Implementation Tasks

### 4.1 Phase 1: Core Analysis

- [ ] Implement `CorrelationResult` dataclass
- [ ] Implement `compute_correlation()` with Pearson/Spearman
- [ ] Implement `_align_timeseries()` helper
- [ ] Write unit tests with synthetic correlated data

### 4.2 Phase 2: Market Discovery

- [ ] Implement `find_correlated_markets()` pairwise comparison
- [ ] Implement `find_inverse_markets()` for binary pairs
- [ ] Add caching for expensive computations
- [ ] Write integration tests

### 4.3 Phase 3: Arbitrage Detection

- [ ] Implement `ArbitrageOpportunity` dataclass
- [ ] Implement `find_arbitrage_opportunities()`
- [ ] Write tests for divergence detection

### 4.4 Phase 4: CLI Integration

- [ ] Add `kalshi data correlations` command
- [ ] Add `kalshi data arbitrage` command
- [ ] Rich table output for results

---

## 5. Acceptance Criteria

1. **Correlation**: Correctly compute Pearson/Spearman for 100+ market pairs
2. **Significance**: Filter by statistical significance (p < 0.05)
3. **Inverse Detection**: Find binary market pairs that should sum to 100%
4. **Arbitrage**: Flag divergence > 10% from expected relationship
5. **Performance**: Analyze 500 markets in < 30 seconds
6. **Tests**: >85% coverage on correlation module

---

## 6. Usage Examples

```python
# Programmatic usage
from kalshi_research.analysis.correlation import CorrelationAnalyzer
from kalshi_research.data import DatabaseManager

async def main():
    db = DatabaseManager("data/kalshi.db")
    analyzer = CorrelationAnalyzer(min_correlation=0.6)

    # Load price snapshots
    async with db.session() as session:
        snapshots = await db.load_price_snapshots(session, days=30)

    # Find correlated markets
    correlated = await analyzer.find_correlated_markets(snapshots, top_n=10)

    for result in correlated:
        print(f"{result.ticker_a} <-> {result.ticker_b}")
        print(f"  Pearson: {result.pearson:.3f} ({result.strength})")
        print(f"  Type: {result.correlation_type.value}")
        print()

    # Find arbitrage
    markets = await fetch_current_markets()
    opportunities = analyzer.find_arbitrage_opportunities(
        markets, correlated, divergence_threshold=0.08
    )

    for opp in opportunities:
        print(f"Arbitrage: {opp.tickers}")
        print(f"  Type: {opp.opportunity_type}")
        print(f"  Divergence: {opp.divergence:.1%}")
```

```bash
# CLI usage
kalshi data correlations --top 20 --min-r 0.6
kalshi data arbitrage
```

---

## 7. Future Considerations

- Lead-lag analysis (which market moves first?)
- Rolling correlation windows for regime detection
- Correlation clustering (group related markets)
- Cross-market correlation (Kalshi vs PredictIt, Polymarket)
- Machine learning for non-linear relationship detection
- Integration with alerts (notify on correlation breakdown)
