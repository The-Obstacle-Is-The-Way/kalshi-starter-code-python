"""
Event correlation analysis for Kalshi markets.

Analyzes how related markets move together to identify:
- Correlated market pairs (positive and negative)
- Arbitrage opportunities from divergence
- Inverse market relationships
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

import numpy as np
from scipy import stats

from kalshi_research.api.models import Market  # noqa: TC001
from kalshi_research.data.models import PriceSnapshot  # noqa: TC001


def _is_priced(market: Market) -> bool:
    """
    Check if a market has meaningful price discovery.

    A market is considered "priced" if it has quotes on both sides.

    This module relies on bid/ask midpoints. If either side is missing
    (commonly represented as `yes_bid == 0` or `yes_ask == 100`), the midpoint
    is not meaningful and can create noisy signals. Kalshi prices are quoted in
    cents of a $1 payout (0-100), so `100` represents $1.00, not $100.00.

    Args:
        market: Market to check

    Returns:
        True if market has meaningful quotes
    """
    return market.yes_bid_cents not in {0, 100} and market.yes_ask_cents not in {0, 100}


class CorrelationType(str, Enum):
    """Types of correlation relationships."""

    POSITIVE = "positive"  # Move together
    NEGATIVE = "negative"  # Move opposite
    LEAD_LAG = "lead_lag"  # One predicts other
    NONE = "none"  # No relationship


@dataclass
class CorrelationResult:
    """Result of correlation analysis between two markets."""

    ticker_a: str
    ticker_b: str
    correlation_type: CorrelationType

    # Correlation metrics
    pearson: float  # Pearson correlation coefficient
    pearson_pvalue: float  # Statistical significance
    spearman: float  # Spearman rank correlation
    spearman_pvalue: float

    # Time window
    start_time: datetime
    end_time: datetime
    n_samples: int

    # Lead-lag analysis (if applicable)
    lead_lag_days: int = 0  # Positive = A leads B
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
    opportunity_type: str  # "divergence", "inverse_sum", "cluster_outlier"
    expected_relationship: str  # What we expect
    actual_values: dict[str, float]
    divergence: float  # Size of mispricing
    confidence: float  # 0-1
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))


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
            start_time = datetime.now(UTC)
            end_time = datetime.now(UTC)

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
            for ticker_b in tickers[i + 1 :]:
                snaps_a = snapshots[ticker_a]
                snaps_b = snapshots[ticker_b]

                # Align by timestamp
                aligned_a, aligned_b, timestamps = self._align_timeseries(snaps_a, snaps_b)

                if len(aligned_a) < self.min_samples:
                    continue

                result = self.compute_correlation(
                    np.array(aligned_a),
                    np.array(aligned_b),
                    ticker_a,
                    ticker_b,
                    timestamps,
                )

                if (
                    result
                    and result.is_significant(self.significance_level)
                    and abs(result.pearson) >= self.min_correlation
                ):
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

        # Group by event, filtering out unpriced markets
        by_event: dict[str, list[Market]] = {}
        for m in markets:
            # SKIP: Unpriced markets (0/0, 0/100 placeholder quotes)
            if not _is_priced(m):
                continue

            event_ticker = m.event_ticker
            if event_ticker not in by_event:
                by_event[event_ticker] = []
            by_event[event_ticker].append(m)

        # Check pairs within same event
        for event_markets in by_event.values():
            if len(event_markets) == 2:
                m1, m2 = event_markets
                # Use midpoint of bid/ask as price
                price1 = m1.midpoint / 100.0
                price2 = m2.midpoint / 100.0
                prob_sum = price1 + price2

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
        # Use midpoint of bid/ask as price
        market_prices = {m.ticker: m.midpoint / 100.0 for m in markets if _is_priced(m)}

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
                    opportunities.append(
                        ArbitrageOpportunity(
                            tickers=[pair.ticker_a, pair.ticker_b],
                            opportunity_type="divergence",
                            expected_relationship=f"Move together (r={pair.pearson:.2f})",
                            actual_values={
                                pair.ticker_a: price_a,
                                pair.ticker_b: price_b,
                            },
                            divergence=divergence,
                            confidence=min(abs(pair.pearson), 1.0),
                        )
                    )

            elif pair.correlation_type == CorrelationType.NEGATIVE:
                # Should sum to ~100%
                prob_sum = price_a + price_b
                if abs(prob_sum - 1.0) > divergence_threshold:
                    opportunities.append(
                        ArbitrageOpportunity(
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
                        )
                    )

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
            key = snap.snapshot_time.replace(minute=0, second=0, microsecond=0).isoformat()
            lookup_a[key] = snap.midpoint

        aligned_a: list[float] = []
        aligned_b: list[float] = []
        timestamps: list[datetime] = []

        for snap in snaps_b:
            key = snap.snapshot_time.replace(minute=0, second=0, microsecond=0).isoformat()
            if key in lookup_a:
                aligned_a.append(lookup_a[key])
                aligned_b.append(snap.midpoint)
                timestamps.append(snap.snapshot_time)

        return aligned_a, aligned_b, timestamps
