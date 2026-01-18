"""Tests for search repository."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from kalshi_research.data.models import Event, Market, PriceSnapshot
from kalshi_research.data.repositories.search import SearchRepository
from kalshi_research.data.search_utils import has_fts5_support


@pytest.fixture
async def sample_data(session: AsyncSession) -> None:
    """Create sample market data for testing."""
    # Create events
    event1 = Event(
        ticker="EVENT-001",
        series_ticker="SERIES-A",
        title="Presidential Election",
        category="Politics",
        status="open",
        mutually_exclusive=True,
    )
    event2 = Event(
        ticker="EVENT-002",
        series_ticker="SERIES-B",
        title="Bitcoin Price",
        category="Crypto",
        status="open",
        mutually_exclusive=False,
    )
    session.add_all([event1, event2])

    # Create markets
    now = datetime.now(UTC)
    market1 = Market(
        ticker="PRES-2024-DEM",
        event_ticker="EVENT-001",
        series_ticker="SERIES-A",
        title="Will Democrat win 2024 election?",
        subtitle="Prediction market for 2024 presidential election",
        status="active",
        result="",
        open_time=now,
        close_time=datetime(2024, 11, 5, tzinfo=UTC),
        expiration_time=datetime(2024, 11, 10, tzinfo=UTC),
        category="Politics",
    )
    market2 = Market(
        ticker="BTC-100K",
        event_ticker="EVENT-002",
        series_ticker="SERIES-B",
        title="Will Bitcoin reach $100,000?",
        subtitle="Bitcoin price prediction",
        status="active",
        result="",
        open_time=now,
        close_time=datetime(2024, 12, 31, tzinfo=UTC),
        expiration_time=datetime(2025, 1, 5, tzinfo=UTC),
        category="Crypto",
    )
    market3 = Market(
        ticker="ETH-5K",
        event_ticker="EVENT-002",
        series_ticker="SERIES-B",
        title="Will Ethereum reach $5,000?",
        subtitle="Ethereum price prediction",
        status="active",
        result="",
        open_time=now,
        close_time=datetime(2024, 12, 31, tzinfo=UTC),
        expiration_time=datetime(2025, 1, 5, tzinfo=UTC),
        category="Crypto",
    )
    session.add_all([market1, market2, market3])

    # Create price snapshots
    snapshot1 = PriceSnapshot(
        ticker="PRES-2024-DEM",
        snapshot_time=now,
        yes_bid=55,
        yes_ask=57,
        no_bid=43,
        no_ask=45,
        last_price=56,
        volume=15000,
        volume_24h=10000,
        open_interest=5000,
    )
    snapshot2 = PriceSnapshot(
        ticker="BTC-100K",
        snapshot_time=now,
        yes_bid=30,
        yes_ask=35,
        no_bid=65,
        no_ask=70,
        last_price=32,
        volume=8000,
        volume_24h=5000,
        open_interest=3000,
    )
    snapshot3 = PriceSnapshot(
        ticker="ETH-5K",
        snapshot_time=now,
        yes_bid=20,
        yes_ask=25,
        no_bid=75,
        no_ask=80,
        last_price=22,
        volume=3000,
        volume_24h=2000,
        open_interest=1000,
    )
    session.add_all([snapshot1, snapshot2, snapshot3])

    await session.commit()


@pytest.mark.asyncio
async def test_fts5_detection(session: AsyncSession) -> None:
    """Test FTS5 availability detection."""
    has_fts5 = await has_fts5_support(session)
    # FTS5 should be available in most modern SQLite builds
    # If not, the test still passes (we just log it)
    assert isinstance(has_fts5, bool)


@pytest.mark.asyncio
async def test_search_markets_like_fallback(
    session: AsyncSession,
    sample_data: None,
) -> None:
    """Test market search using LIKE fallback (always works)."""
    _ = sample_data  # Ensure fixture is executed
    repo = SearchRepository(session)

    # Search for "Bitcoin"
    results = await repo.search_markets("Bitcoin", limit=10)
    assert len(results) >= 1
    assert any("Bitcoin" in r.title for r in results)

    # Search for "election"
    results = await repo.search_markets("election", limit=10)
    assert len(results) >= 1
    assert any("election" in r.title.lower() for r in results)


@pytest.mark.asyncio
async def test_search_markets_with_status_filter(
    session: AsyncSession,
    sample_data: None,
) -> None:
    """Test market search with status filter."""
    _ = sample_data  # Ensure fixture is executed
    repo = SearchRepository(session)

    # Search with status filter
    results = await repo.search_markets("Bitcoin", status="active", limit=10)
    assert len(results) >= 1
    for result in results:
        assert result.status == "active"


@pytest.mark.asyncio
async def test_search_markets_with_category_filter(
    session: AsyncSession,
    sample_data: None,
) -> None:
    """Test market search with category filter."""
    _ = sample_data  # Ensure fixture is executed
    repo = SearchRepository(session)

    # Search with category filter
    results = await repo.search_markets("price", category="Crypto", limit=10)
    assert len(results) >= 1
    for result in results:
        assert result.event_category == "Crypto"


@pytest.mark.asyncio
async def test_search_markets_with_volume_filter(
    session: AsyncSession,
    sample_data: None,
) -> None:
    """Test market search with minimum volume filter."""
    _ = sample_data  # Ensure fixture is executed
    repo = SearchRepository(session)

    # Search with minimum volume filter
    results = await repo.search_markets("", min_volume=5000, limit=10)
    assert len(results) >= 1
    for result in results:
        assert result.volume_24h is not None
        assert result.volume_24h >= 5000


@pytest.mark.asyncio
async def test_search_markets_no_results(
    session: AsyncSession,
    sample_data: None,
) -> None:
    """Test market search returns empty list when no matches."""
    _ = sample_data  # Ensure fixture is executed
    repo = SearchRepository(session)

    # Search for non-existent term
    results = await repo.search_markets("XYZNONEXISTENT", limit=10)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_search_markets_limit(
    session: AsyncSession,
    sample_data: None,
) -> None:
    """Test market search respects limit parameter."""
    _ = sample_data  # Ensure fixture is executed
    repo = SearchRepository(session)

    # Search with limit
    results = await repo.search_markets("", limit=2)
    assert len(results) <= 2
