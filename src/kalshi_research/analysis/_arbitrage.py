"""
Arbitrage detection functions for correlation analysis.
"""

from __future__ import annotations

from typing import cast

from kalshi_research.analysis._correlation_models import (
    ArbitrageOpportunity,
    CorrelationResult,
    CorrelationType,
    _is_priced,
)
from kalshi_research.api.models import Market  # noqa: TC001


def find_inverse_markets(
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
            midpoint1 = cast("float", m1.midpoint)
            midpoint2 = cast("float", m2.midpoint)
            prob_sum = (midpoint1 + midpoint2) / 100.0

            if abs(prob_sum - 1.0) > tolerance:
                deviation = prob_sum - 1.0
                results.append((m1, m2, deviation))

    return results


def find_inverse_market_groups(
    markets: list[Market],
    tolerance: float = 0.05,
) -> list[tuple[list[Market], float]]:
    """
    Find event market groups that should sum to ~100%.

    This is most useful for events with 2+ mutually exclusive outcomes (multi-choice events).
    For each event, it checks whether the sum of YES midpoints is close to 1.0.

    Notes:
        - This method skips events where *any* market is unpriced/placeholder, since a partial
          sum is not meaningful.

    Args:
        markets: List of markets to analyze
        tolerance: Allowed deviation from 100%

    Returns:
        List of (event_markets, sum_deviation) tuples where sum_deviation = sum(prob) - 1.0
    """
    results: list[tuple[list[Market], float]] = []

    by_event_all: dict[str, list[Market]] = {}
    for market in markets:
        by_event_all.setdefault(market.event_ticker, []).append(market)

    for event_markets in by_event_all.values():
        priced = [m for m in event_markets if _is_priced(m)]
        if len(priced) != len(event_markets):
            continue
        if len(priced) < 2:
            continue

        priced.sort(key=lambda m: m.ticker)
        midpoints = [cast("float", m.midpoint) for m in priced]
        prob_sum = sum(midpoints) / 100.0
        deviation = prob_sum - 1.0

        if abs(deviation) > tolerance:
            results.append((priced, deviation))

    return results


def find_arbitrage_opportunities(
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
    market_prices: dict[str, float] = {}
    for m in markets:
        if not _is_priced(m):
            continue
        midpoint = cast("float", m.midpoint)
        market_prices[m.ticker] = midpoint / 100.0

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
