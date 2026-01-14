"""
Tests for correlation analysis - uses REAL numpy arrays and scipy stats.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import pytest

from kalshi_research.analysis.correlation import (
    CorrelationAnalyzer,
    CorrelationResult,
    CorrelationType,
)
from kalshi_research.api.models import Market, MarketStatus
from kalshi_research.data.models import PriceSnapshot


def make_snapshot(ticker: str, timestamp: datetime, yes_price: float) -> PriceSnapshot:
    """Helper to create PriceSnapshot for testing."""
    # PriceSnapshot is an ORM model - we create it without session
    snap = PriceSnapshot()
    snap.ticker = ticker
    snap.snapshot_time = timestamp
    yes_cents = int(yes_price * 100)
    snap.yes_bid = max(0, yes_cents - 1)
    snap.yes_ask = min(100, yes_cents + 1)
    snap.no_bid = max(0, 100 - snap.yes_ask)
    snap.no_ask = min(100, 100 - snap.yes_bid)
    snap.last_price = yes_cents
    snap.volume = 100
    snap.volume_24h = 50
    snap.open_interest = 200
    return snap


def make_market(
    ticker: str,
    event_ticker: str,
    yes_price: int,
    **kwargs: Any,
) -> Market:
    """Helper to create Market for testing."""
    defaults = {
        "ticker": ticker,
        "event_ticker": event_ticker,
        "title": f"Market {ticker}",
        "subtitle": "",
        "status": MarketStatus.ACTIVE,
        "result": "",
        "yes_bid": yes_price - 1,
        "yes_ask": yes_price + 1,
        "no_bid": 100 - yes_price - 1,
        "no_ask": 100 - yes_price + 1,
        "last_price": yes_price,
        "volume": 1000,
        "volume_24h": 500,
        "open_interest": 800,
        "open_time": datetime(2024, 1, 1, tzinfo=UTC),
        "close_time": datetime(2025, 1, 1, tzinfo=UTC),
        "expiration_time": datetime(2025, 1, 2, tzinfo=UTC),
        "liquidity": 10000,
    }
    defaults.update(kwargs)
    return Market(**defaults)


class TestCorrelationResult:
    """Test CorrelationResult dataclass."""

    def test_is_significant(self) -> None:
        """Check if correlation is statistically significant."""
        result = CorrelationResult(
            ticker_a="BTC-100K",
            ticker_b="BTC-110K",
            correlation_type=CorrelationType.POSITIVE,
            pearson=0.85,
            pearson_pvalue=0.001,
            spearman=0.82,
            spearman_pvalue=0.002,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            n_samples=100,
        )

        assert result.is_significant(alpha=0.05) is True
        assert result.is_significant(alpha=0.0001) is False

    def test_strength_property(self) -> None:
        """Test correlation strength categorization."""
        now = datetime.now(UTC)

        # Weak correlation
        weak = CorrelationResult(
            ticker_a="A",
            ticker_b="B",
            correlation_type=CorrelationType.POSITIVE,
            pearson=0.2,
            pearson_pvalue=0.05,
            spearman=0.2,
            spearman_pvalue=0.05,
            start_time=now,
            end_time=now,
            n_samples=30,
        )
        assert weak.strength == "weak"

        # Moderate correlation
        moderate = CorrelationResult(
            ticker_a="A",
            ticker_b="B",
            correlation_type=CorrelationType.POSITIVE,
            pearson=0.5,
            pearson_pvalue=0.05,
            spearman=0.5,
            spearman_pvalue=0.05,
            start_time=now,
            end_time=now,
            n_samples=30,
        )
        assert moderate.strength == "moderate"

        # Strong correlation
        strong = CorrelationResult(
            ticker_a="A",
            ticker_b="B",
            correlation_type=CorrelationType.POSITIVE,
            pearson=0.85,
            pearson_pvalue=0.001,
            spearman=0.85,
            spearman_pvalue=0.001,
            start_time=now,
            end_time=now,
            n_samples=30,
        )
        assert strong.strength == "strong"

        # Negative correlation should use absolute value
        negative = CorrelationResult(
            ticker_a="A",
            ticker_b="B",
            correlation_type=CorrelationType.NEGATIVE,
            pearson=-0.8,
            pearson_pvalue=0.001,
            spearman=-0.8,
            spearman_pvalue=0.001,
            start_time=now,
            end_time=now,
            n_samples=30,
        )
        assert negative.strength == "strong"


class TestComputeCorrelation:
    """Test correlation computation."""

    def test_perfect_positive_correlation(self) -> None:
        """Perfect positive correlation gives r=1.0."""
        analyzer = CorrelationAnalyzer(min_samples=3)

        prices_a = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        prices_b = np.array([0.1, 0.2, 0.3, 0.4, 0.5])

        result = analyzer.compute_correlation(prices_a, prices_b, "A", "B")

        assert result is not None
        assert result.pearson == pytest.approx(1.0)
        assert result.correlation_type == CorrelationType.POSITIVE
        assert result.n_samples == 5

    def test_perfect_negative_correlation(self) -> None:
        """Perfect negative correlation gives r=-1.0."""
        analyzer = CorrelationAnalyzer(min_samples=3)

        prices_a = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        prices_b = np.array([0.5, 0.4, 0.3, 0.2, 0.1])

        result = analyzer.compute_correlation(prices_a, prices_b, "A", "B")

        assert result is not None
        assert result.pearson == pytest.approx(-1.0)
        assert result.correlation_type == CorrelationType.NEGATIVE
        assert result.spearman == pytest.approx(-1.0)

    def test_no_correlation(self) -> None:
        """No correlation gives r≈0."""
        analyzer = CorrelationAnalyzer(min_samples=5)

        # Random uncorrelated data
        np.random.seed(42)
        prices_a = np.random.random(50)
        prices_b = np.random.random(50)

        result = analyzer.compute_correlation(prices_a, prices_b, "A", "B")

        assert result is not None
        assert abs(result.pearson) < 0.3
        assert result.correlation_type == CorrelationType.NONE

    def test_handles_nan_values(self) -> None:
        """NaN values are filtered out."""
        analyzer = CorrelationAnalyzer(min_samples=3)

        prices_a = np.array([0.1, np.nan, 0.3, 0.4, 0.5])
        prices_b = np.array([0.1, 0.2, np.nan, 0.4, 0.5])

        result = analyzer.compute_correlation(prices_a, prices_b, "A", "B")

        assert result is not None
        # Should have 3 valid samples (indices 0, 3, 4)
        assert result.n_samples == 3

    def test_insufficient_samples_returns_none(self) -> None:
        """Returns None if too few samples."""
        analyzer = CorrelationAnalyzer(min_samples=30)

        prices_a = np.array([0.1, 0.2, 0.3])
        prices_b = np.array([0.1, 0.2, 0.3])

        result = analyzer.compute_correlation(prices_a, prices_b, "A", "B")

        assert result is None

    def test_mismatched_lengths_returns_none(self) -> None:
        """Returns None if arrays have different lengths."""
        analyzer = CorrelationAnalyzer(min_samples=3)

        prices_a = np.array([0.1, 0.2, 0.3])
        prices_b = np.array([0.1, 0.2])

        result = analyzer.compute_correlation(prices_a, prices_b, "A", "B")

        assert result is None

    def test_with_timestamps(self) -> None:
        """Timestamps are used for time bounds."""
        analyzer = CorrelationAnalyzer(min_samples=3)

        prices_a = np.array([0.1, 0.2, 0.3])
        prices_b = np.array([0.1, 0.2, 0.3])

        start = datetime(2024, 1, 1, tzinfo=UTC)
        timestamps = [
            start,
            start + timedelta(days=1),
            start + timedelta(days=2),
        ]

        result = analyzer.compute_correlation(prices_a, prices_b, "A", "B", timestamps)

        assert result is not None
        assert result.start_time == start
        assert result.end_time == start + timedelta(days=2)


class TestFindCorrelatedMarkets:
    """Test finding correlated market pairs."""

    @pytest.mark.asyncio
    async def test_finds_correlated_pairs(self) -> None:
        """Finds pairs with strong correlation."""
        analyzer = CorrelationAnalyzer(min_samples=10, min_correlation=0.5)

        # Create synthetic correlated data
        now = datetime.now(UTC)
        timestamps = [now + timedelta(hours=i) for i in range(50)]

        # Market A and B are strongly correlated
        prices_a = [0.5 + i * 0.01 for i in range(50)]
        prices_b = [0.5 + i * 0.01 + np.random.normal(0, 0.01) for i in range(50)]

        # Market C is uncorrelated
        prices_c = [0.5 + np.random.normal(0, 0.1) for _ in range(50)]

        snapshots = {
            "A": [make_snapshot("A", t, p) for t, p in zip(timestamps, prices_a, strict=True)],
            "B": [make_snapshot("B", t, p) for t, p in zip(timestamps, prices_b, strict=True)],
            "C": [make_snapshot("C", t, p) for t, p in zip(timestamps, prices_c, strict=True)],
        }

        results = await analyzer.find_correlated_markets(snapshots, top_n=10)

        # Should find A-B correlation but not A-C or B-C
        assert len(results) >= 1

        # First result should be A-B
        top = results[0]
        assert {top.ticker_a, top.ticker_b} == {"A", "B"}
        assert abs(top.pearson) > 0.5
        assert top.is_significant()

    @pytest.mark.asyncio
    async def test_returns_top_n_results(self) -> None:
        """Returns only top N correlations."""
        analyzer = CorrelationAnalyzer(min_samples=10, min_correlation=0.3)

        # Create 5 markets with varying correlations
        now = datetime.now(UTC)
        timestamps = [now + timedelta(hours=i) for i in range(30)]

        snapshots = {}
        for i in range(5):
            prices = [0.5 + j * 0.01 + np.random.normal(0, 0.02) for j in range(30)]
            snapshots[f"M{i}"] = [
                make_snapshot(f"M{i}", t, p) for t, p in zip(timestamps, prices, strict=True)
            ]

        # Request top 3
        results = await analyzer.find_correlated_markets(snapshots, top_n=3)

        # Should have at most 3 results
        assert len(results) <= 3

        # Should be sorted by absolute correlation
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert abs(results[i].pearson) >= abs(results[i + 1].pearson)

    @pytest.mark.asyncio
    async def test_filters_by_min_correlation(self) -> None:
        """Only returns correlations above threshold."""
        analyzer = CorrelationAnalyzer(min_samples=10, min_correlation=0.8)

        # Create weakly correlated markets
        now = datetime.now(UTC)
        timestamps = [now + timedelta(hours=i) for i in range(30)]

        prices_a = [0.5 + np.random.normal(0, 0.1) for _ in range(30)]
        prices_b = [0.5 + np.random.normal(0, 0.1) for _ in range(30)]

        snapshots = {
            "A": [make_snapshot("A", t, p) for t, p in zip(timestamps, prices_a, strict=True)],
            "B": [make_snapshot("B", t, p) for t, p in zip(timestamps, prices_b, strict=True)],
        }

        results = await analyzer.find_correlated_markets(snapshots, top_n=10)

        # Should find no correlations above 0.8
        assert len(results) == 0


class TestFindInverseMarkets:
    """Test finding inverse market pairs."""

    def test_finds_inverse_pairs_in_same_event(self) -> None:
        """Finds pairs within same event that should sum to 100%."""
        analyzer = CorrelationAnalyzer()

        markets = [
            make_market("EVENT-YES", "EVENT", 55),
            make_market("EVENT-NO", "EVENT", 50),
        ]

        results = analyzer.find_inverse_markets(markets, tolerance=0.05)

        assert len(results) == 1
        m1, m2, deviation = results[0]
        assert {m1.ticker, m2.ticker} == {"EVENT-YES", "EVENT-NO"}
        # 55% + 50% = 105% = 1.05, deviation = 0.05
        assert abs(deviation - 0.05) < 0.01

    def test_ignores_correct_inverse_pairs(self) -> None:
        """Doesn't flag pairs that sum to ~100%."""
        analyzer = CorrelationAnalyzer()

        markets = [
            make_market("EVENT-YES", "EVENT", 48),
            make_market("EVENT-NO", "EVENT", 52),
        ]

        results = analyzer.find_inverse_markets(markets, tolerance=0.05)

        # 48% + 52% = 100%, within tolerance
        assert len(results) == 0

    def test_handles_multiple_events(self) -> None:
        """Processes multiple events separately."""
        analyzer = CorrelationAnalyzer()

        markets = [
            # Event 1 - has divergence
            make_market("E1-YES", "E1", 60),
            make_market("E1-NO", "E1", 50),
            # Event 2 - no divergence
            make_market("E2-YES", "E2", 48),
            make_market("E2-NO", "E2", 52),
        ]

        results = analyzer.find_inverse_markets(markets, tolerance=0.05)

        # Should only flag E1
        assert len(results) == 1
        m1, m2, _ = results[0]
        assert m1.event_ticker == "E1"
        assert m2.event_ticker == "E1"

    def test_excludes_unpriced_and_placeholder_markets(self) -> None:
        """Markets without two-sided quotes should not create inverse pairs."""
        analyzer = CorrelationAnalyzer()

        markets = [
            # Event A: both priced -> should be considered
            make_market("A-YES", "A", 65),
            make_market("A-NO", "A", 50),
            # Event B: one unpriced (0/0) -> excluded
            make_market("B-YES", "B", 55),
            make_market(
                "B-NO",
                "B",
                50,
                yes_bid=0,
                yes_ask=0,
                no_bid=0,
                no_ask=0,
                last_price=None,
            ),
            # Event C: one placeholder (0/100) -> excluded
            make_market("C-YES", "C", 55),
            make_market(
                "C-NO",
                "C",
                50,
                yes_bid=0,
                yes_ask=100,
                no_bid=0,
                no_ask=100,
                last_price=None,
            ),
            # Event D: one-sided markets (no bid / no ask) -> excluded
            make_market(
                "D-YES",
                "D",
                50,
                yes_bid=0,
                yes_ask=40,
                no_bid=60,
                no_ask=100,
                last_price=None,
            ),
            make_market(
                "D-NO",
                "D",
                50,
                yes_bid=99,
                yes_ask=100,
                no_bid=0,
                no_ask=1,
                last_price=None,
            ),
        ]

        results = analyzer.find_inverse_markets(markets, tolerance=0.10)

        event_tickers = {m1.event_ticker for m1, _m2, _dev in results}
        assert "A" in event_tickers
        assert "B" not in event_tickers
        assert "C" not in event_tickers
        assert "D" not in event_tickers


class TestFindInverseMarketGroups:
    """Test finding inverse market groups within an event."""

    def test_finds_multi_market_event_groups(self) -> None:
        """Events with 3+ priced markets should be checked as a group."""
        analyzer = CorrelationAnalyzer()

        markets = [
            make_market("A", "E", 31),
            make_market("B", "E", 31),
            make_market("C", "E", 31),
        ]

        results = analyzer.find_inverse_market_groups(markets, tolerance=0.05)

        assert len(results) == 1
        group, deviation = results[0]
        assert [m.ticker for m in group] == ["A", "B", "C"]
        assert abs(deviation - (-0.07)) < 0.01

    def test_skips_events_with_less_than_two_priced_markets(self) -> None:
        """Single-market events should be ignored (need 2+ priced markets to sum)."""
        analyzer = CorrelationAnalyzer()

        markets = [make_market("A", "E", 31)]
        results = analyzer.find_inverse_market_groups(markets, tolerance=0.05)

        assert results == []

    def test_skips_events_with_any_unpriced_market(self) -> None:
        """Partial sums are not meaningful when an event has unpriced markets."""
        analyzer = CorrelationAnalyzer()

        markets = [
            make_market("A", "E", 31),
            make_market("B", "E", 31),
            make_market(
                "C",
                "E",
                31,
                yes_bid=0,
                yes_ask=100,
                no_bid=0,
                no_ask=100,
                last_price=None,
            ),
        ]

        results = analyzer.find_inverse_market_groups(markets, tolerance=0.05)
        assert results == []


class TestIsPriced:
    """Test _is_priced helper."""

    def test_is_priced_helper(self) -> None:
        """Detect unpriced, placeholder, and one-sided markets."""
        from kalshi_research.analysis.correlation import _is_priced

        assert not _is_priced(
            make_market(
                "UNPRICED_00",
                "E",
                50,
                yes_bid=0,
                yes_ask=0,
                no_bid=0,
                no_ask=0,
                last_price=None,
            )
        )
        assert not _is_priced(
            make_market(
                "PLACEHOLDER_0_100",
                "E",
                50,
                yes_bid=0,
                yes_ask=100,
                no_bid=0,
                no_ask=100,
                last_price=None,
            )
        )
        assert not _is_priced(
            make_market(
                "NO_BID",
                "E",
                50,
                yes_bid=0,
                yes_ask=40,
                no_bid=60,
                no_ask=100,
                last_price=None,
            )
        )
        assert not _is_priced(
            make_market(
                "NO_ASK",
                "E",
                50,
                yes_bid=99,
                yes_ask=100,
                no_bid=0,
                no_ask=1,
                last_price=None,
            )
        )
        assert _is_priced(make_market("PRICED", "E", 50))


class TestFindArbitrageOpportunities:
    """Test arbitrage detection."""

    def test_detects_positive_correlation_divergence(self) -> None:
        """Flags when positively correlated markets diverge."""
        analyzer = CorrelationAnalyzer()

        # Create correlation result showing strong positive correlation
        correlated_pairs = [
            CorrelationResult(
                ticker_a="BTC-100K",
                ticker_b="BTC-110K",
                correlation_type=CorrelationType.POSITIVE,
                pearson=0.9,
                pearson_pvalue=0.001,
                spearman=0.88,
                spearman_pvalue=0.001,
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                n_samples=100,
            )
        ]

        # Current prices show divergence
        markets = [
            make_market("BTC-100K", "BTC", 70),
            make_market("BTC-110K", "BTC", 50),
        ]

        opportunities = analyzer.find_arbitrage_opportunities(
            markets, correlated_pairs, divergence_threshold=0.10
        )

        assert len(opportunities) == 1
        opp = opportunities[0]
        assert opp.opportunity_type == "divergence"
        assert set(opp.tickers) == {"BTC-100K", "BTC-110K"}
        assert opp.divergence == pytest.approx(0.2)  # 70% - 50% = 20%
        assert opp.confidence == pytest.approx(0.9)

    def test_detects_negative_correlation_sum_error(self) -> None:
        """Flags when negatively correlated markets don't sum to 100%."""
        analyzer = CorrelationAnalyzer()

        correlated_pairs = [
            CorrelationResult(
                ticker_a="TRUMP-WIN",
                ticker_b="BIDEN-WIN",
                correlation_type=CorrelationType.NEGATIVE,
                pearson=-0.95,
                pearson_pvalue=0.001,
                spearman=-0.93,
                spearman_pvalue=0.001,
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                n_samples=100,
            )
        ]

        markets = [
            make_market("TRUMP-WIN", "ELECTION", 55),
            make_market("BIDEN-WIN", "ELECTION", 50),
        ]

        opportunities = analyzer.find_arbitrage_opportunities(
            markets, correlated_pairs, divergence_threshold=0.03
        )

        assert len(opportunities) == 1
        opp = opportunities[0]
        assert opp.opportunity_type == "inverse_sum"
        assert set(opp.tickers) == {"TRUMP-WIN", "BIDEN-WIN"}
        # 55% + 50% = 105% = 1.05, divergence = 0.05
        assert opp.divergence == pytest.approx(0.05)

    def test_ignores_small_divergences(self) -> None:
        """Doesn't flag divergences below threshold."""
        analyzer = CorrelationAnalyzer()

        correlated_pairs = [
            CorrelationResult(
                ticker_a="A",
                ticker_b="B",
                correlation_type=CorrelationType.POSITIVE,
                pearson=0.8,
                pearson_pvalue=0.01,
                spearman=0.78,
                spearman_pvalue=0.01,
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                n_samples=50,
            )
        ]

        markets = [
            make_market("A", "TEST", 51),
            make_market("B", "TEST", 50),
        ]

        opportunities = analyzer.find_arbitrage_opportunities(
            markets, correlated_pairs, divergence_threshold=0.10
        )

        # Divergence is only 1%, below 10% threshold
        assert len(opportunities) == 0

    def test_handles_missing_markets(self) -> None:
        """Gracefully handles when market data is missing."""
        analyzer = CorrelationAnalyzer()

        correlated_pairs = [
            CorrelationResult(
                ticker_a="A",
                ticker_b="B",
                correlation_type=CorrelationType.POSITIVE,
                pearson=0.8,
                pearson_pvalue=0.01,
                spearman=0.78,
                spearman_pvalue=0.01,
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                n_samples=50,
            )
        ]

        # Only market A exists, B is missing
        markets = [
            make_market("A", "TEST", 50),
        ]

        opportunities = analyzer.find_arbitrage_opportunities(
            markets, correlated_pairs, divergence_threshold=0.10
        )

        # Should return empty list, not crash
        assert len(opportunities) == 0


class TestAlignTimeseries:
    """Test time series alignment helper."""

    def test_aligns_by_hour(self) -> None:
        """Aligns two time series by hour."""
        analyzer = CorrelationAnalyzer()

        base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

        snaps_a = [
            make_snapshot("A", base_time + timedelta(hours=i, minutes=15), 0.5 + i * 0.01)
            for i in range(5)
        ]

        snaps_b = [
            make_snapshot("B", base_time + timedelta(hours=i, minutes=45), 0.6 + i * 0.01)
            for i in range(5)
        ]

        aligned_a, aligned_b, timestamps = analyzer._align_timeseries(snaps_a, snaps_b)

        # Should align all 5 hours
        assert len(aligned_a) == 5
        assert len(aligned_b) == 5
        assert len(timestamps) == 5

        # Check values are correct (midpoint returns cents, 0-100)
        for i in range(5):
            assert aligned_a[i] == pytest.approx((0.5 + i * 0.01) * 100)
            assert aligned_b[i] == pytest.approx((0.6 + i * 0.01) * 100)

    def test_handles_missing_timestamps(self) -> None:
        """Only returns aligned timestamps."""
        analyzer = CorrelationAnalyzer()

        base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

        # A has hours 0, 1, 2, 3, 4
        snaps_a = [make_snapshot("A", base_time + timedelta(hours=i), 0.5) for i in range(5)]

        # B has hours 1, 3, 5 (only 1 and 3 overlap)
        snaps_b = [make_snapshot("B", base_time + timedelta(hours=i), 0.6) for i in [1, 3, 5]]

        aligned_a, aligned_b, timestamps = analyzer._align_timeseries(snaps_a, snaps_b)

        # Should only have 2 aligned points (hours 1 and 3)
        assert len(aligned_a) == 2
        assert len(aligned_b) == 2
        assert len(timestamps) == 2
