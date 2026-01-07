# BUG-004: Missing Analysis Modules

**Priority:** P3
**Status:** Open
**Discovered:** 2026-01-06
**Spec Reference:** SPEC-004 Section 3.1

---

## Summary

Several analysis modules specified in SPEC-004 are missing from `src/kalshi_research/analysis/`.

## Expected Files (per SPEC-004)

```
analysis/
├── __init__.py          ✓ EXISTS
├── calibration.py       ✓ EXISTS
├── edge.py              ✓ EXISTS
├── scanner.py           ✓ EXISTS
├── correlation.py       ✗ MISSING
├── metrics.py           ✗ MISSING
└── visualization.py     ✗ MISSING
```

## Missing Modules

### 1. `correlation.py`
Event correlation analysis for related markets.

Key features needed:
- Detect correlated market pairs
- Analyze price movement correlation
- Identify arbitrage opportunities between related events

### 2. `metrics.py`
Market efficiency metrics per SPEC-004 Section 2.3.

Required metrics:
- Spread analysis (Ask - Bid)
- Depth (volume at best prices)
- Volatility calculation
- Volume profile analysis

### 3. `visualization.py`
Chart generation helpers.

Required visualizations:
- Calibration curve plotting
- Probability timeline
- Edge histogram
- Price/volume charts

## Impact

- Cannot analyze market correlations (correlation.py)
- Cannot compute efficiency metrics (metrics.py)
- Cannot generate charts programmatically (visualization.py)

## Fix

Implement the three missing modules with the following interfaces:

```python
# correlation.py
class CorrelationAnalyzer:
    def find_correlated_markets(self, markets: list[Market]) -> list[tuple[str, str, float]]: ...
    def analyze_pair_correlation(self, ticker1: str, ticker2: str) -> dict: ...

# metrics.py
class MarketMetrics:
    def compute_spread_stats(self, market: Market) -> dict: ...
    def compute_volatility(self, snapshots: list[PriceSnapshot]) -> float: ...
    def compute_volume_profile(self, snapshots: list[PriceSnapshot]) -> dict: ...

# visualization.py
def plot_calibration_curve(result: CalibrationResult) -> Figure: ...
def plot_probability_timeline(snapshots: list[PriceSnapshot]) -> Figure: ...
def plot_edge_histogram(edges: list[Edge]) -> Figure: ...
```

## Acceptance Criteria

- [ ] `correlation.py` implemented with correlation analysis
- [ ] `metrics.py` implemented with efficiency metrics
- [ ] `visualization.py` implemented with matplotlib charts
- [ ] All modules have >85% test coverage
- [ ] All modules pass mypy --strict
