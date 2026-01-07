"""Unit tests for market metrics computation."""

from datetime import UTC, datetime, timedelta

import pytest

from kalshi_research.analysis.metrics import (
    MarketMetrics,
    SpreadStats,
    VolatilityStats,
    VolumeProfile,
)
from kalshi_research.api.models import Market, MarketStatus
from kalshi_research.data.models import PriceSnapshot


@pytest.fixture
def sample_market() -> Market:
    """Create a sample Market for testing."""
    return Market(
        ticker="TEST-25JAN-T50",
        event_ticker="TEST-25JAN",
        title="Test Market",
        subtitle="Testing only",
        status=MarketStatus.ACTIVE,
        yes_bid=45,
        yes_ask=47,
        no_bid=53,
        no_ask=55,
        last_price=46,
        volume=1000,
        volume_24h=500,
        open_interest=100,
        open_time=datetime(2025, 1, 1, tzinfo=UTC),
        close_time=datetime(2025, 1, 31, tzinfo=UTC),
        expiration_time=datetime(2025, 2, 1, tzinfo=UTC),
        liquidity=10000,
    )


@pytest.fixture
def sample_snapshots() -> list[PriceSnapshot]:
    """Create sample price snapshots for testing."""
    base_time = datetime(2025, 1, 1, tzinfo=UTC)
    snapshots = []

    for i in range(10):
        snap = PriceSnapshot(
            id=i + 1,
            ticker="TEST-25JAN-T50",
            snapshot_time=base_time + timedelta(hours=i),
            yes_bid=45 + i,
            yes_ask=47 + i,
            no_bid=53 - i,
            no_ask=55 - i,
            last_price=46 + i,
            volume=100 + i * 10,
            volume_24h=50 + i * 5,
            open_interest=100,
            liquidity=10000,
        )
        snapshots.append(snap)

    return snapshots


class TestMarketMetrics:
    """Tests for MarketMetrics class."""

    def test_compute_spread_stats_current_only(self, sample_market: Market) -> None:
        """Test spread computation with market data only."""
        metrics = MarketMetrics()

        spread = metrics.compute_spread_stats(sample_market)

        assert isinstance(spread, SpreadStats)
        assert spread.ticker == "TEST-25JAN-T50"
        assert spread.current_spread == 2  # 47 - 45
        assert spread.avg_spread == 2.0
        assert spread.min_spread == 2
        assert spread.max_spread == 2
        assert spread.n_samples == 1
        # Midpoint = (45 + 47) / 2 = 46
        # Relative spread = 2 / 46 ≈ 0.0435
        assert abs(spread.relative_spread - 0.04347826) < 0.00001

    def test_compute_spread_stats_with_history(
        self, sample_market: Market, sample_snapshots: list[PriceSnapshot]
    ) -> None:
        """Test spread computation with historical snapshots."""
        metrics = MarketMetrics()

        spread = metrics.compute_spread_stats(sample_market, sample_snapshots)

        assert spread.ticker == "TEST-25JAN-T50"
        assert spread.current_spread == 2  # From market
        assert spread.avg_spread == 2.0  # All snapshots have spread of 2
        assert spread.min_spread == 2
        assert spread.max_spread == 2
        assert spread.n_samples == 10

    def test_compute_spread_stats_zero_midpoint(self) -> None:
        """Test spread computation when midpoint is zero (edge case)."""
        market = Market(
            ticker="ZERO-TEST",
            event_ticker="ZERO",
            title="Zero test",
            status=MarketStatus.ACTIVE,
            yes_bid=0,
            yes_ask=0,
            no_bid=100,
            no_ask=100,
            volume=0,
            volume_24h=0,
            open_interest=0,
            open_time=datetime(2025, 1, 1, tzinfo=UTC),
            close_time=datetime(2025, 1, 31, tzinfo=UTC),
            expiration_time=datetime(2025, 2, 1, tzinfo=UTC),
            liquidity=0,
        )

        metrics = MarketMetrics()
        spread = metrics.compute_spread_stats(market)

        assert spread.relative_spread == 0.0  # Should handle division by zero

    def test_compute_volatility_basic(self, sample_snapshots: list[PriceSnapshot]) -> None:
        """Test basic volatility computation."""
        metrics = MarketMetrics()

        vol = metrics.compute_volatility(sample_snapshots)

        assert vol is not None
        assert isinstance(vol, VolatilityStats)
        assert vol.ticker == "TEST-25JAN-T50"
        assert vol.hourly_volatility > 0
        assert vol.daily_volatility > 0
        assert vol.max_daily_move >= 0
        assert vol.avg_abs_return >= 0
        assert vol.period_days > 0

    def test_compute_volatility_insufficient_data(self) -> None:
        """Test volatility with insufficient data."""
        metrics = MarketMetrics()

        # Single snapshot
        single_snap = PriceSnapshot(
            id=1,
            ticker="TEST",
            snapshot_time=datetime(2025, 1, 1, tzinfo=UTC),
            yes_bid=50,
            yes_ask=50,
            no_bid=50,
            no_ask=50,
            volume=0,
            volume_24h=0,
            open_interest=0,
            liquidity=0,
        )

        vol = metrics.compute_volatility([single_snap])
        assert vol is None

    def test_compute_volatility_zero_prices(self) -> None:
        """Test volatility computation with zero prices (edge case)."""
        base_time = datetime(2025, 1, 1, tzinfo=UTC)
        snapshots = [
            PriceSnapshot(
                id=1,
                ticker="ZERO",
                snapshot_time=base_time,
                yes_bid=0,
                yes_ask=0,
                no_bid=100,
                no_ask=100,
                volume=0,
                volume_24h=0,
                open_interest=0,
                liquidity=0,
            ),
            PriceSnapshot(
                id=2,
                ticker="ZERO",
                snapshot_time=base_time + timedelta(hours=1),
                yes_bid=0,
                yes_ask=0,
                no_bid=100,
                no_ask=100,
                volume=0,
                volume_24h=0,
                open_interest=0,
                liquidity=0,
            ),
        ]

        metrics = MarketMetrics()
        vol = metrics.compute_volatility(snapshots)

        # Should return None due to infinite/nan returns
        assert vol is None

    def test_compute_volume_profile(self, sample_snapshots: list[PriceSnapshot]) -> None:
        """Test volume profile computation."""
        metrics = MarketMetrics()

        profile = metrics.compute_volume_profile(sample_snapshots)

        assert profile is not None
        assert isinstance(profile, VolumeProfile)
        assert profile.ticker == "TEST-25JAN-T50"
        assert len(profile.hourly_volume) == 24
        assert len(profile.daily_volume) == 7
        assert profile.total_volume > 0
        assert profile.period_days >= 0

    def test_compute_volume_profile_empty(self) -> None:
        """Test volume profile with no data."""
        metrics = MarketMetrics()

        profile = metrics.compute_volume_profile([])
        assert profile is None

    def test_compute_volume_profile_hourly_distribution(self) -> None:
        """Test that hourly volume is correctly distributed."""
        base_time = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)  # Noon
        snapshots = [
            PriceSnapshot(
                id=i,
                ticker="TEST",
                snapshot_time=base_time + timedelta(hours=i),
                yes_bid=50,
                yes_ask=50,
                no_bid=50,
                no_ask=50,
                volume=100 * (i + 1),  # Increasing volume
                volume_24h=50,
                open_interest=100,
                liquidity=1000,
            )
            for i in range(24)
        ]

        metrics = MarketMetrics()
        profile = metrics.compute_volume_profile(snapshots)

        assert profile is not None
        # Hour 12 should have volume from first snapshot
        assert profile.hourly_volume[12] == 100.0
        # Hour 13 should have volume from second snapshot
        assert profile.hourly_volume[13] == 200.0


class TestSpreadStats:
    """Tests for SpreadStats dataclass."""

    def test_spread_stats_creation(self) -> None:
        """Test creating SpreadStats."""
        stats = SpreadStats(
            ticker="TEST",
            current_spread=2,
            avg_spread=2.5,
            min_spread=1,
            max_spread=5,
            relative_spread=0.05,
            n_samples=100,
        )

        assert stats.ticker == "TEST"
        assert stats.current_spread == 2
        assert stats.avg_spread == 2.5


class TestVolatilityStats:
    """Tests for VolatilityStats dataclass."""

    def test_volatility_stats_creation(self) -> None:
        """Test creating VolatilityStats."""
        stats = VolatilityStats(
            ticker="TEST",
            daily_volatility=0.15,
            hourly_volatility=0.03,
            max_daily_move=0.25,
            avg_abs_return=0.02,
            period_days=30,
        )

        assert stats.ticker == "TEST"
        assert stats.daily_volatility == 0.15


class TestVolumeProfile:
    """Tests for VolumeProfile dataclass."""

    def test_volume_profile_creation(self) -> None:
        """Test creating VolumeProfile."""
        profile = VolumeProfile(
            ticker="TEST",
            hourly_volume={i: float(i * 100) for i in range(24)},
            daily_volume={
                "Mon": 1000.0,
                "Tue": 1500.0,
                "Wed": 1200.0,
                "Thu": 1100.0,
                "Fri": 1300.0,
                "Sat": 500.0,
                "Sun": 400.0,
            },
            total_volume=10000,
            period_days=7,
        )

        assert profile.ticker == "TEST"
        assert profile.total_volume == 10000
        assert len(profile.hourly_volume) == 24
