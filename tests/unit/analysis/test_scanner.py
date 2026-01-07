"""
Tests for market scanner - uses REAL objects.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from kalshi_research.analysis.scanner import MarketScanner, ScanFilter, ScanResult
from kalshi_research.api.models.market import Market, MarketStatus


def make_market(
    ticker: str,
    yes_bid: int = 45,
    yes_ask: int = 55,
    volume_24h: int = 5000,
    close_time: datetime | None = None,
) -> Market:
    """Helper to create test markets."""
    if close_time is None:
        close_time = datetime.now(UTC) + timedelta(days=1)
    return Market(
        ticker=ticker,
        event_ticker="EVENT-1",
        title=f"Test Market {ticker}",
        status=MarketStatus.ACTIVE,
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


class TestScanAll:
    """Test scan_all method."""

    def test_returns_all_filter_types(self) -> None:
        """Returns results for all filter types."""
        scanner = MarketScanner(
            close_race_range=(0.40, 0.60),
            high_volume_threshold=10000,
            wide_spread_threshold=5,
        )
        now = datetime.now(UTC)
        markets = [
            make_market(
                "ALL",
                yes_bid=45,
                yes_ask=55,
                volume_24h=20000,
                close_time=now + timedelta(hours=12),
            ),
        ]

        results = scanner.scan_all(markets)

        assert ScanFilter.CLOSE_RACE in results
        assert ScanFilter.HIGH_VOLUME in results
        assert ScanFilter.WIDE_SPREAD in results
        assert ScanFilter.EXPIRING_SOON in results
