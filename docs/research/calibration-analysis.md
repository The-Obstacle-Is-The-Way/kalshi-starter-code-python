# Calibration Analysis (Explanation)

Calibration answers the most important question for any forecaster: **"Are my probabilities accurate?"**

A perfectly calibrated predictor assigns probabilities that match actual frequencies. If you say something has a 70%
chance of happening, and you make 100 such predictions, exactly 70 of them should come true.

## Why Calibration Matters

Most people are poorly calibrated:

- **Overconfidence**: Saying 90% when it's really 60%
- **Underconfidence**: Saying 50% when it's really 80%
- **Extremity aversion**: Avoiding 5% or 95% predictions

Poor calibration means you're systematically wrong, which bleeds money in prediction markets.

## The Brier Score

The fundamental metric for probabilistic predictions:

```python
brier_score = (1/N) * Σ(forecast - outcome)²
```

Where:

- `forecast` is your probability (0 to 1)
- `outcome` is what happened (0 for NO, 1 for YES)

### Interpreting Brier Scores

| Score | Interpretation |
|-------|----------------|
| 0.00 | Perfect (you predicted 1.0 for all YES, 0.0 for all NO) |
| 0.10 | Excellent |
| 0.15 | Good |
| 0.20 | Fair |
| 0.25 | Random guessing (always predict 50%) |
| 0.33 | Bad (worse than random) |
| 1.00 | Perfectly wrong |

## Brier Decomposition

The Brier score can be broken down into three components that tell you *why* you're scoring the way you are:

```
Brier = Reliability - Resolution + Uncertainty
```

### Reliability (Calibration Error)

How well your probabilities match actual frequencies.

```python
reliability = Σ(n_k * (o_k - f_k)²) / N
```

Where:

- `n_k` = samples in bin k
- `o_k` = actual YES frequency in bin k
- `f_k` = mean predicted probability in bin k

**Lower is better.** Zero means perfect calibration.

### Resolution (Discrimination)

How much your predictions vary from the base rate. Can you distinguish likely from unlikely events?

```python
resolution = Σ(n_k * (o_k - base_rate)²) / N
```

**Higher is better.** If you always predict the base rate, resolution is zero (no discrimination).

### Uncertainty

The inherent unpredictability of the events:

```python
uncertainty = base_rate * (1 - base_rate)
```

This is fixed by the data - you can't control it.

### The Relationship

```
Brier = Reliability - Resolution + Uncertainty
```

To get a good Brier score:

- Minimize reliability (be well-calibrated)
- Maximize resolution (make confident, varying predictions)

## Brier Skill Score

Compares your Brier score to a baseline (always predicting the base rate):

```python
skill_score = 1 - (brier / climatology_brier)
```

Where `climatology_brier = base_rate * (1 - base_rate)`.

- Skill > 0: You're better than guessing the base rate
- Skill = 0: You're no better than always guessing the base rate
- Skill < 0: You're worse than the baseline (ouch)

## Calibration Curves

A calibration curve plots predicted probabilities vs actual frequencies:

```text
Actual Frequency
    1.0 │                              ╱
        │                           ╱
        │                        ╱ ●
    0.5 │                     ╱ ●
        │                  ╱ ●
        │               ╱ ●
    0.0 │────●───●───╱──────────────────
        0   0.2  0.4  0.6  0.8  1.0
              Predicted Probability
```

The diagonal line is perfect calibration. Points above the line mean underconfidence; below means overconfidence.

## CalibrationResult Data

The analyzer returns:

```python
@dataclass
class CalibrationResult:
    brier_score: float
    brier_skill_score: float
    n_samples: int

    # Calibration curve data
    bins: NDArray              # Probability bin edges
    predicted_probs: NDArray   # Mean predicted prob per bin
    actual_freqs: NDArray      # Actual YES frequency per bin
    bin_counts: NDArray        # Samples per bin

    # Brier decomposition
    reliability: float
    resolution: float
    uncertainty: float
```

## CLI Usage

Run calibration analysis on your historical data:

```bash
# Last 30 days
uv run kalshi analysis calibration --db data/kalshi.db --days 30

# Save results to file
uv run kalshi analysis calibration --db data/kalshi.db --days 30 --output calibration.json
```

## What the Data Shows

The calibration analysis uses:

1. **Price snapshots**: What the market predicted at various times
2. **Settlements**: What actually happened

It bins market prices (e.g., 0-10%, 10-20%, ..., 90-100%) and compares to actual YES frequencies.

This tells you if Kalshi markets are well-calibrated (they generally are), and helps you spot where markets might be
systematically miscalibrated.

## Using for Your Theses

You can compute calibration on your personal theses:

```python
from kalshi_research.analysis.calibration import CalibrationAnalyzer
from kalshi_research.research.thesis import ThesisTracker

tracker = ThesisTracker()
resolved = tracker.list_resolved()

forecasts = [t.your_probability for t in resolved]
outcomes = [1 if t.actual_outcome == "yes" else 0 for t in resolved]

analyzer = CalibrationAnalyzer(n_bins=5)  # Fewer bins for small samples
result = analyzer.compute_calibration(forecasts, outcomes)

print(result)
```

## Sample Size Considerations

Calibration analysis needs sufficient data:

- **< 20 samples**: Results are noise, don't trust them
- **20-50 samples**: Directional signal, but wide confidence intervals
- **50-100 samples**: Starting to be meaningful
- **100+ samples**: Reliable metrics

With small samples, use fewer bins (5 instead of 10) to get enough data per bin.

## Key Code

- Analyzer: `src/kalshi_research/analysis/calibration.py`
- CLI command: `src/kalshi_research/cli/analysis.py`

## See Also

- [Thesis System](thesis-system.md) - Track your predictions
- [Backtesting](backtesting.md) - Simulate P&L
- [Usage: Analysis](../getting-started/usage.md#analysis-db-backed) - CLI commands
