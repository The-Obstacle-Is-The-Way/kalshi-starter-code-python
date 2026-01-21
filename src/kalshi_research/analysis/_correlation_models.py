"""
Models and types for correlation analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kalshi_research.api.models import Market


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
    yes_bid = market.yes_bid_cents
    yes_ask = market.yes_ask_cents
    if yes_bid is None or yes_ask is None:
        return False
    return yes_bid not in {0, 100} and yes_ask not in {0, 100}


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
