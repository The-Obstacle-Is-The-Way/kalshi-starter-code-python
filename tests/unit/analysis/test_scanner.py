"""
Tests for market scanner - uses REAL objects.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from kalshi_research.analysis.scanner import (
    MarketClosedError,
    MarketScanner,
    MarketStatusVerifier,
    ScanFilter,
    ScanResult,
)
from kalshi_research.api.models.market import Market, MarketStatus


def make_market(
    ticker: str,
    yes_bid: int = 45,
    yes_ask: int = 55,
    volume_24h: int = 5000,
    close_time: datetime | None = None,
    status: MarketStatus = MarketStatus.ACTIVE,
) -> Market:
    """Helper to create test markets."""
    if close_time is None:
        close_time = datetime.now(UTC) + timedelta(days=1)
    return Market(
        ticker=ticker,
        event_ticker="EVENT-1",
        title=f"Test Market {ticker}",
        status=status,
        yes_bid=yes_bid,
        yes_ask=yes_ask,
        no_bid=100 - yes_ask,
        no_ask=100 - yes_bid,
        volume=10000,
        volume_24h=volume_24h,
        open_interest=1000,
        open_time=datetime.now(UTC) - timedelta(days=1),
        close_time=close_time,
        expiration_time=close_time,
        liquidity=50000,
    )


class TestMarketStatusVerifier:
    """Test MarketStatusVerifier class."""

    def test_is_market_tradeable_active_and_open(self) -> None:
        """Active market before close_time is tradeable."""
        verifier = MarketStatusVerifier()
        market = make_market(
            "TEST",
            status=MarketStatus.ACTIVE,
            close_time=datetime.now(UTC) + timedelta(hours=1),
        )

        assert verifier.is_market_tradeable(market) is True

    def test_is_market_tradeable_closed_status(self) -> None:
        """Market with CLOSED status is not tradeable."""
        verifier = MarketStatusVerifier()
        market = make_market(
            "TEST",
            status=MarketStatus.CLOSED,
            close_time=datetime.now(UTC) + timedelta(hours=1),
        )

        assert verifier.is_market_tradeable(market) is False

    def test_is_market_tradeable_past_close_time(self) -> None:
        """Market past close_time is not tradeable."""
        verifier = MarketStatusVerifier()
        market = make_market(
            "TEST",
            status=MarketStatus.ACTIVE,
            close_time=datetime.now(UTC) - timedelta(hours=1),
        )

        assert verifier.is_market_tradeable(market) is False

    def test_verify_market_open_raises_on_closed_status(self) -> None:
        """verify_market_open raises MarketClosedError for non-active status."""
        verifier = MarketStatusVerifier()
        market = make_market(
            "TEST",
            status=MarketStatus.CLOSED,
            close_time=datetime.now(UTC) + timedelta(hours=1),
        )

        with pytest.raises(MarketClosedError, match="has status closed"):
            verifier.verify_market_open(market)

    def test_verify_market_open_raises_on_past_close_time(self) -> None:
        """verify_market_open raises MarketClosedError for past close_time."""
        verifier = MarketStatusVerifier()
        market = make_market(
            "TEST",
            status=MarketStatus.ACTIVE,
            close_time=datetime.now(UTC) - timedelta(hours=1),
        )

        with pytest.raises(MarketClosedError, match="closed at"):
            verifier.verify_market_open(market)

    def test_verify_market_open_succeeds_for_tradeable(self) -> None:
        """verify_market_open succeeds for tradeable market."""
        verifier = MarketStatusVerifier()
        market = make_market(
            "TEST",
            status=MarketStatus.ACTIVE,
            close_time=datetime.now(UTC) + timedelta(hours=1),
        )

        # Should not raise
        verifier.verify_market_open(market)

    def test_filter_tradeable_markets(self) -> None:
        """filter_tradeable_markets filters out non-tradeable markets."""
        verifier = MarketStatusVerifier()
        now = datetime.now(UTC)
        markets = [
            make_market("ACTIVE", status=MarketStatus.ACTIVE, close_time=now + timedelta(hours=1)),
            make_market("CLOSED", status=MarketStatus.CLOSED, close_time=now + timedelta(hours=1)),
            make_market(
                "PAST_CLOSE",
                status=MarketStatus.ACTIVE,
                close_time=now - timedelta(hours=1),
            ),
            make_market("ACTIVE2", status=MarketStatus.ACTIVE, close_time=now + timedelta(hours=2)),
        ]

        tradeable = verifier.filter_tradeable_markets(markets)

        assert len(tradeable) == 2
        assert tradeable[0].ticker == "ACTIVE"
        assert tradeable[1].ticker == "ACTIVE2"


class TestScanResult:
    """Test ScanResult dataclass."""

    def test_str_representation(self) -> None:
        """String representation is readable."""
        result = ScanResult(
            ticker="TEST-MKT",
            title="Test Market Title That Is Long",
            filter_type=ScanFilter.CLOSE_RACE,
            score=0.8,
            market_prob=0.50,
            volume_24h=10000,
            spread=5,
        )

        string = str(result)
        assert "CLOSE_RACE" in string
        assert "TEST-MKT" in string
        assert "50%" in string


class TestCloseRaceScan:
    """Test scanning for close races."""

    def test_finds_close_races(self) -> None:
        """Finds markets near 50%."""
        scanner = MarketScanner()
        markets = [
            make_market("CLOSE-1", yes_bid=48, yes_ask=52),  # 50% - very close
            make_market("CLOSE-2", yes_bid=45, yes_ask=55),  # 50% - close
            make_market("FAR-1", yes_bid=10, yes_ask=20),  # 15% - far
        ]

        results = scanner.scan_close_races(markets)

        assert len(results) == 2
        assert results[0].ticker == "CLOSE-1"  # Closer to 50%

    def test_respects_top_n(self) -> None:
        """Respects top_n limit."""
        scanner = MarketScanner()
        markets = [make_market(f"MKT-{i}", yes_bid=48, yes_ask=52) for i in range(10)]

        results = scanner.scan_close_races(markets, top_n=3)

        assert len(results) == 3

    def test_excludes_outside_range(self) -> None:
        """Excludes markets outside close race range."""
        scanner = MarketScanner(close_race_range=(0.40, 0.60))
        markets = [
            make_market("FAR", yes_bid=70, yes_ask=80),  # 75% - outside
        ]

        results = scanner.scan_close_races(markets)

        assert len(results) == 0

    def test_excludes_unpriced_and_placeholder_markets(self) -> None:
        """Unpriced markets (0/0, 0/100) should be excluded from close-race scan."""
        scanner = MarketScanner()
        markets = [
            make_market("PRICED", yes_bid=48, yes_ask=52, volume_24h=1000),
            make_market("UNPRICED_00", yes_bid=0, yes_ask=0, volume_24h=0),
            make_market("PLACEHOLDER_0_100", yes_bid=0, yes_ask=100, volume_24h=0),
        ]

        results = scanner.scan_close_races(markets, top_n=10)

        tickers = {r.ticker for r in results}
        assert "PRICED" in tickers
        assert "UNPRICED_00" not in tickers
        assert "PLACEHOLDER_0_100" not in tickers

    def test_respects_min_volume_24h(self) -> None:
        """Markets below min_volume_24h should be excluded."""
        scanner = MarketScanner()
        markets = [
            make_market("HIGH_VOL", yes_bid=48, yes_ask=52, volume_24h=10_000),
            make_market("LOW_VOL", yes_bid=48, yes_ask=52, volume_24h=100),
        ]

        results = scanner.scan_close_races(markets, top_n=10, min_volume_24h=1000)

        tickers = {r.ticker for r in results}
        assert "HIGH_VOL" in tickers
        assert "LOW_VOL" not in tickers

    def test_respects_max_spread(self) -> None:
        """Markets with spread > max_spread should be excluded."""
        scanner = MarketScanner()
        markets = [
            make_market("TIGHT", yes_bid=48, yes_ask=52, volume_24h=1000),  # spread=4
            make_market("WIDE", yes_bid=20, yes_ask=80, volume_24h=1000),  # spread=60
        ]

        results = scanner.scan_close_races(markets, top_n=10, max_spread=10)

        tickers = {r.ticker for r in results}
        assert "TIGHT" in tickers
        assert "WIDE" not in tickers

    def test_excludes_closed_markets(self) -> None:
        """Closed markets should never appear in close race results."""
        scanner = MarketScanner()
        now = datetime.now(UTC)
        markets = [
            make_market("OPEN", yes_bid=48, yes_ask=52, close_time=now + timedelta(hours=1)),
            make_market(
                "CLOSED_STATUS",
                yes_bid=48,
                yes_ask=52,
                status=MarketStatus.CLOSED,
                close_time=now + timedelta(hours=1),
            ),
            make_market(
                "PAST_CLOSE",
                yes_bid=48,
                yes_ask=52,
                close_time=now - timedelta(minutes=5),
            ),
        ]

        results = scanner.scan_close_races(markets, top_n=10)

        tickers = {r.ticker for r in results}
        assert "OPEN" in tickers
        assert "CLOSED_STATUS" not in tickers
        assert "PAST_CLOSE" not in tickers  # This was the bug - closed 5 minutes ago!


class TestHighVolumeScan:
    """Test scanning for high volume."""

    def test_finds_high_volume(self) -> None:
        """Finds markets with high volume."""
        scanner = MarketScanner(high_volume_threshold=10000)
        markets = [
            make_market("HIGH-1", volume_24h=50000),
            make_market("HIGH-2", volume_24h=20000),
            make_market("LOW-1", volume_24h=5000),
        ]

        results = scanner.scan_high_volume(markets)

        assert len(results) == 2
        assert results[0].ticker == "HIGH-1"

    def test_excludes_low_volume(self) -> None:
        """Excludes markets below threshold."""
        scanner = MarketScanner(high_volume_threshold=10000)
        markets = [make_market("LOW", volume_24h=1000)]

        results = scanner.scan_high_volume(markets)

        assert len(results) == 0


class TestWideSpreadScan:
    """Test scanning for wide spreads."""

    def test_finds_wide_spreads(self) -> None:
        """Finds markets with wide spreads."""
        scanner = MarketScanner(wide_spread_threshold=5)
        markets = [
            make_market("WIDE-1", yes_bid=40, yes_ask=55),  # 15c spread
            make_market("WIDE-2", yes_bid=45, yes_ask=55),  # 10c spread
            make_market("TIGHT", yes_bid=49, yes_ask=51),  # 2c spread
        ]

        results = scanner.scan_wide_spread(markets)

        assert len(results) == 2
        assert results[0].ticker == "WIDE-1"

    def test_excludes_tight_spreads(self) -> None:
        """Excludes tight spreads."""
        scanner = MarketScanner(wide_spread_threshold=5)
        markets = [make_market("TIGHT", yes_bid=49, yes_ask=51)]

        results = scanner.scan_wide_spread(markets)

        assert len(results) == 0


class TestExpiringSoonScan:
    """Test scanning for expiring markets."""

    def test_finds_expiring_markets(self) -> None:
        """Finds markets expiring soon."""
        scanner = MarketScanner()
        now = datetime.now(UTC)
        markets = [
            make_market("SOON-1", close_time=now + timedelta(hours=2)),
            make_market("SOON-2", close_time=now + timedelta(hours=12)),
            make_market("LATER", close_time=now + timedelta(days=7)),
        ]

        results = scanner.scan_expiring_soon(markets, hours=24)

        assert len(results) == 2
        assert results[0].ticker == "SOON-1"  # Closest expiry

    def test_excludes_distant_expiry(self) -> None:
        """Excludes markets with distant expiry."""
        scanner = MarketScanner()
        now = datetime.now(UTC)
        markets = [make_market("FAR", close_time=now + timedelta(days=30))]

        results = scanner.scan_expiring_soon(markets, hours=24)

        assert len(results) == 0
