"""
Event correlation analysis for Kalshi markets.

Analyzes how related markets move together to identify:
- Correlated market pairs (positive and negative)
- Arbitrage opportunities from divergence
- Inverse market relationships
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import numpy as np
from scipy import stats

# Re-export models for backwards compatibility
from kalshi_research.analysis._arbitrage import (
    find_arbitrage_opportunities,
    find_inverse_market_groups,
    find_inverse_markets,
)
from kalshi_research.analysis._correlation_models import (
    ArbitrageOpportunity,
    CorrelationResult,
    CorrelationType,
    _is_priced,
)

if TYPE_CHECKING:
    from kalshi_research.api.models import Market
    from kalshi_research.data.models import PriceSnapshot

__all__ = [
    "ArbitrageOpportunity",
    "CorrelationAnalyzer",
    "CorrelationResult",
    "CorrelationType",
    "_is_priced",
]


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

        Delegates to module-level function for implementation.

        Args:
            markets: List of markets to analyze
            tolerance: Allowed deviation from 100%

        Returns:
            List of (market_a, market_b, sum_deviation) tuples
        """
        return find_inverse_markets(markets, tolerance)

    def find_inverse_market_groups(
        self,
        markets: list[Market],
        tolerance: float = 0.05,
    ) -> list[tuple[list[Market], float]]:
        """
        Find event market groups that should sum to ~100%.

        Delegates to module-level function for implementation.

        Args:
            markets: List of markets to analyze
            tolerance: Allowed deviation from 100%

        Returns:
            List of (event_markets, sum_deviation) tuples
        """
        return find_inverse_market_groups(markets, tolerance)

    def find_arbitrage_opportunities(
        self,
        markets: list[Market],
        correlated_pairs: list[CorrelationResult],
        divergence_threshold: float = 0.10,
    ) -> list[ArbitrageOpportunity]:
        """
        Find potential arbitrage from correlated markets diverging.

        Delegates to module-level function for implementation.

        Args:
            markets: Current market data
            correlated_pairs: Known correlated pairs
            divergence_threshold: Min divergence to flag

        Returns:
            List of arbitrage opportunities
        """
        return find_arbitrage_opportunities(markets, correlated_pairs, divergence_threshold)

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
