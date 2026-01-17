from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kalshi_research.api.models.event import Event
from kalshi_research.api.models.market import Market, MarketFilterStatus, MarketStatus
from kalshi_research.data.fetcher import DataFetcher


@pytest.fixture
def mock_db():
    """Create a mock DatabaseManager with proper async session handling.

    The mock needs to support:
        async with self._db.session_factory() as session, session.begin():
            ...

    This means:
    1. session_factory() returns an async context manager
    2. The context manager's __aenter__ returns the session
    3. session.begin() returns an async context manager
    """
    db = MagicMock()
    session = AsyncMock()

    # session.begin() returns an async context manager
    begin_cm = AsyncMock()
    begin_cm.__aenter__.return_value = None
    begin_cm.__aexit__.return_value = None
    session.begin = MagicMock(return_value=begin_cm)

    # Create an async context manager that yields the session
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None

    # session_factory() should return the async context manager
    db.session_factory = MagicMock(return_value=session_cm)

    # Expose session for assertions in tests.
    db._session = session

    return db


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    return client


@pytest.fixture
def data_fetcher(mock_db, mock_client):
    return DataFetcher(mock_db, mock_client)


def test_api_market_to_settlement_falls_back_to_expiration_time(data_fetcher) -> None:
    """When settlement_ts is missing, use expiration_time as a documented proxy."""
    from datetime import UTC, datetime, timedelta

    base = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)

    market = Market(
        ticker="TEST-MARKET",
        event_ticker="TEST-EVENT",
        series_ticker=None,
        title="Test Market",
        subtitle="",
        status=MarketStatus.FINALIZED,
        result="yes",
        yes_bid=50,
        yes_ask=52,
        no_bid=48,
        no_ask=50,
        last_price=51,
        volume=100,
        volume_24h=10,
        open_interest=20,
        open_time=base - timedelta(days=3),
        close_time=base - timedelta(days=2),
        expiration_time=base - timedelta(days=1),
        settlement_ts=None,
        liquidity=1000,
    )

    settlement = data_fetcher._api_market_to_settlement(market)
    assert settlement is not None
    assert settlement.settled_at == market.expiration_time


@pytest.mark.asyncio
async def test_sync_events(data_fetcher, mock_client, mock_db):
    # Mock API events
    mock_event = Event(
        event_ticker="TEST-EVENT",
        series_ticker="TEST-SERIES",
        title="Test Event",
        category="Test",
    )

    async def event_gen(limit: int = 200, max_pages: int | None = None):
        yield mock_event

    mock_client.get_all_events = MagicMock(side_effect=event_gen)

    # Mock repository
    with patch("kalshi_research.data.fetcher.EventRepository") as MockRepo:
        mock_repo = AsyncMock()
        MockRepo.return_value = mock_repo

        count = await data_fetcher.sync_events()

        assert count == 1
        mock_repo.upsert.assert_called_once()
        mock_repo.commit.assert_not_called()
        mock_db._session.begin.assert_called_once()


@pytest.mark.asyncio
async def test_sync_events_does_not_call_multivariate_when_disabled(
    data_fetcher, mock_client, mock_db
):
    mock_event = Event(
        event_ticker="TEST-EVENT",
        series_ticker="TEST-SERIES",
        title="Test Event",
        category="Test",
    )

    async def event_gen(limit: int = 200, max_pages: int | None = None):
        yield mock_event

    async def mve_event_gen(limit: int = 200, max_pages: int | None = None):
        yield Event(
            event_ticker="TEST-MVE-EVENT",
            series_ticker="TEST-MVE-SERIES",
            title="Test MVE Event",
            category="Sports",
        )

    mock_client.get_all_events = MagicMock(side_effect=event_gen)
    mock_client.get_all_multivariate_events = MagicMock(side_effect=mve_event_gen)

    with patch("kalshi_research.data.fetcher.EventRepository") as MockRepo:
        mock_repo = AsyncMock()
        MockRepo.return_value = mock_repo

        count = await data_fetcher.sync_events(include_multivariate=False)

    assert count == 1
    mock_client.get_all_multivariate_events.assert_not_called()
    mock_db._session.begin.assert_called_once()


@pytest.mark.asyncio
async def test_sync_events_includes_multivariate_events_when_enabled(
    data_fetcher, mock_client, mock_db
):
    mock_event = Event(
        event_ticker="TEST-EVENT",
        series_ticker="TEST-SERIES",
        title="Test Event",
        category="Test",
    )

    mock_mve_event = Event(
        event_ticker="TEST-MVE-EVENT",
        series_ticker="TEST-MVE-SERIES",
        title="Test MVE Event",
        category="Sports",
    )

    async def event_gen(limit: int = 200, max_pages: int | None = None):
        yield mock_event

    async def mve_event_gen(limit: int = 200, max_pages: int | None = None):
        yield mock_mve_event

    mock_client.get_all_events = MagicMock(side_effect=event_gen)
    mock_client.get_all_multivariate_events = MagicMock(side_effect=mve_event_gen)

    with patch("kalshi_research.data.fetcher.EventRepository") as MockRepo:
        mock_repo = AsyncMock()
        MockRepo.return_value = mock_repo

        count = await data_fetcher.sync_events(include_multivariate=True)

        assert count == 2
        assert mock_repo.upsert.call_count == 2
        mock_db._session.begin.assert_called_once()


@pytest.mark.asyncio
async def test_sync_events_flushes_on_multivariate_boundary(data_fetcher, mock_client, mock_db):
    """Ensure flush cadence remains correct when MVEs are appended after regular events."""

    async def event_gen(limit: int = 200, max_pages: int | None = None):
        for i in range(99):
            yield Event(
                event_ticker=f"TEST-EVENT-{i}",
                series_ticker="TEST-SERIES",
                title=f"Test Event {i}",
                category="Test",
            )

    async def mve_event_gen(limit: int = 200, max_pages: int | None = None):
        yield Event(
            event_ticker="TEST-MVE-EVENT",
            series_ticker="TEST-MVE-SERIES",
            title="Test MVE Event",
            category="Sports",
        )

    mock_client.get_all_events = MagicMock(side_effect=event_gen)
    mock_client.get_all_multivariate_events = MagicMock(side_effect=mve_event_gen)
    mock_db._session.flush = AsyncMock()

    with patch("kalshi_research.data.fetcher.EventRepository") as MockRepo:
        mock_repo = AsyncMock()
        MockRepo.return_value = mock_repo

        count = await data_fetcher.sync_events(include_multivariate=True)

    assert count == 100
    mock_db._session.flush.assert_awaited_once()
    mock_db._session.begin.assert_called_once()


@pytest.mark.asyncio
async def test_sync_markets(data_fetcher, mock_client, mock_db):
    from datetime import UTC, datetime

    api_market = Market(
        ticker="TEST-MARKET",
        event_ticker="TEST-EVENT",
        series_ticker="TEST-SERIES",
        title="Test Market",
        subtitle="Subtitle",
        status=MarketStatus.ACTIVE,
        result="",
        volume=0,
        volume_24h=0,
        open_interest=0,
        open_time=datetime(2024, 1, 1, tzinfo=UTC),
        close_time=datetime(2025, 1, 1, tzinfo=UTC),
        expiration_time=datetime(2025, 1, 1, tzinfo=UTC),
    )

    # Correctly mock async generator
    async def market_gen(status=None, max_pages: int | None = None, mve_filter=None):
        yield api_market

    # REPLACE the AsyncMock method with a MagicMock that returns the generator
    mock_client.get_all_markets = MagicMock(side_effect=market_gen)

    # Mock repositories
    with (
        patch("kalshi_research.data.fetcher.MarketRepository") as MockMarketRepo,
        patch("kalshi_research.data.fetcher.EventRepository") as MockEventRepo,
    ):
        market_repo = AsyncMock()
        MockMarketRepo.return_value = market_repo

        event_repo = AsyncMock()
        MockEventRepo.return_value = event_repo

        count = await data_fetcher.sync_markets()

        assert count == 1
        event_repo.insert_ignore.assert_awaited_once()
        market_repo.upsert.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_settlements(data_fetcher, mock_client, mock_db):
    # Mock settled API market
    from datetime import UTC, datetime, timedelta

    expiration_time = datetime.now(UTC) - timedelta(days=1)

    api_market = Market(
        ticker="TEST-MARKET",
        event_ticker="TEST-EVENT",
        series_ticker="TEST-SERIES",
        title="Test Market",
        subtitle="Subtitle",
        status=MarketStatus.FINALIZED,
        result="yes",
        volume=0,
        volume_24h=0,
        open_interest=0,
        open_time=datetime.now(UTC) - timedelta(days=2),
        close_time=datetime.now(UTC) - timedelta(days=1),
        expiration_time=expiration_time,
        settlement_ts=expiration_time - timedelta(hours=1),
    )

    async def market_gen(status=None, max_pages: int | None = None, mve_filter=None):
        del mve_filter
        yield api_market

    mock_client.get_all_markets = MagicMock(side_effect=market_gen)

    with (
        patch("kalshi_research.data.fetcher.SettlementRepository") as MockSettlementRepo,
        patch("kalshi_research.data.fetcher.MarketRepository") as MockMarketRepo,
        patch("kalshi_research.data.fetcher.EventRepository") as MockEventRepo,
    ):
        settlement_repo = AsyncMock()
        MockSettlementRepo.return_value = settlement_repo

        market_repo = AsyncMock()
        MockMarketRepo.return_value = market_repo

        event_repo = AsyncMock()
        MockEventRepo.return_value = event_repo

        count = await data_fetcher.sync_settlements()

        assert count == 1
        event_repo.insert_ignore.assert_awaited_once()
        settlement_repo.upsert.assert_awaited_once()
        market_repo.upsert.assert_awaited_once()
        mock_client.get_all_markets.assert_called_once_with(
            status=MarketFilterStatus.SETTLED, max_pages=None
        )


@pytest.mark.asyncio
async def test_take_snapshot(data_fetcher, mock_client, mock_db):
    from datetime import UTC, datetime, timedelta

    mock_market = Market(
        ticker="TEST-MARKET",
        event_ticker="TEST-EVENT",
        series_ticker=None,
        title="Test Market",
        subtitle="",
        status=MarketStatus.ACTIVE,
        result="",
        yes_bid=50,
        yes_ask=52,
        yes_bid_dollars="0.50",
        yes_ask_dollars="0.52",
        no_bid=48,
        no_ask=50,
        no_bid_dollars="0.48",
        no_ask_dollars="0.50",
        last_price=51,
        last_price_dollars="0.51",
        volume=1000,
        volume_24h=100,
        open_interest=500,
        open_time=datetime.now(UTC) - timedelta(days=1),
        close_time=datetime.now(UTC) + timedelta(days=1),
        expiration_time=datetime.now(UTC) + timedelta(days=2),
        liquidity=10000,
    )

    async def market_gen(status=None, max_pages: int | None = None, mve_filter=None):
        del mve_filter
        yield mock_market

    mock_client.get_all_markets = MagicMock(side_effect=market_gen)

    with patch("kalshi_research.data.fetcher.PriceRepository") as MockPriceRepo:
        repo = AsyncMock()
        MockPriceRepo.return_value = repo

        count = await data_fetcher.take_snapshot(max_pages=5)

        assert count == 1
        repo.add.assert_called_once()
        mock_client.get_all_markets.assert_called_once_with(status="open", max_pages=5)
        # With session.begin() pattern, commits are automatic on context exit


@pytest.mark.asyncio
async def test_full_sync(data_fetcher):
    data_fetcher.sync_events = AsyncMock(return_value=5)
    data_fetcher.sync_markets = AsyncMock(return_value=10)
    data_fetcher.take_snapshot = AsyncMock(return_value=100)

    result = await data_fetcher.full_sync()

    assert result["events"] == 5
    assert result["markets"] == 10
    assert result["snapshots"] == 100


@pytest.mark.asyncio
async def test_take_snapshot_creates_missing_market_and_event(tmp_path) -> None:
    """Snapshot should auto-create missing market/event rows (FK robustness)."""
    from datetime import UTC, datetime, timedelta

    from kalshi_research.data import DatabaseManager
    from kalshi_research.data.repositories import EventRepository, MarketRepository, PriceRepository

    db_path = tmp_path / "kalshi_fetcher_fk.db"

    api_market = Market(
        ticker="TEST-MARKET",
        event_ticker="TEST-EVENT",
        series_ticker=None,
        title="Test Market",
        subtitle="",
        status=MarketStatus.ACTIVE,
        result="",
        yes_bid=50,
        yes_ask=52,
        yes_bid_dollars="0.50",
        yes_ask_dollars="0.52",
        no_bid=48,
        no_ask=50,
        no_bid_dollars="0.48",
        no_ask_dollars="0.50",
        last_price=51,
        last_price_dollars="0.51",
        volume=100,
        volume_24h=10,
        open_interest=20,
        open_time=datetime.now(UTC) - timedelta(days=1),
        close_time=datetime.now(UTC) + timedelta(days=1),
        expiration_time=datetime.now(UTC) + timedelta(days=2),
        liquidity=1000,
    )

    class StubClient:
        async def get_all_markets(self, *args, **kwargs):
            yield api_market

    async with DatabaseManager(db_path) as db:
        await db.create_tables()
        async with DataFetcher(db, client=StubClient()) as fetcher:
            count = await fetcher.take_snapshot(status="open")

        assert count == 1

        async with db.session_factory() as session:
            event_repo = EventRepository(session)
            market_repo = MarketRepository(session)
            price_repo = PriceRepository(session)

            assert await event_repo.get("TEST-EVENT") is not None
            assert await market_repo.get("TEST-MARKET") is not None
            assert await price_repo.get_latest("TEST-MARKET") is not None


@pytest.mark.asyncio
async def test_sync_settlements_creates_missing_market_event_and_settlement(tmp_path) -> None:
    """Settlements sync should auto-create missing market/event rows (FK robustness)."""
    from datetime import UTC, datetime, timedelta

    from kalshi_research.data import DatabaseManager
    from kalshi_research.data.repositories import (
        EventRepository,
        MarketRepository,
        SettlementRepository,
    )

    db_path = tmp_path / "kalshi_fetcher_settlements_fk.db"

    expiration_time = datetime.now(UTC) - timedelta(days=1)
    settlement_ts = expiration_time - timedelta(hours=1)

    api_market = Market(
        ticker="TEST-MARKET",
        event_ticker="TEST-EVENT",
        series_ticker=None,
        title="Test Market",
        subtitle="",
        status=MarketStatus.FINALIZED,
        result="yes",
        yes_bid=50,
        yes_ask=52,
        no_bid=48,
        no_ask=50,
        last_price=51,
        volume=100,
        volume_24h=10,
        open_interest=20,
        open_time=datetime.now(UTC) - timedelta(days=3),
        close_time=datetime.now(UTC) - timedelta(days=2),
        expiration_time=expiration_time,
        settlement_ts=settlement_ts,
        liquidity=1000,
    )

    class StubClient:
        async def get_all_markets(self, *args, **kwargs):
            yield api_market

    async with DatabaseManager(db_path) as db:
        await db.create_tables()
        async with DataFetcher(db, client=StubClient()) as fetcher:
            count = await fetcher.sync_settlements()

        assert count == 1

        async with db.session_factory() as session:
            event_repo = EventRepository(session)
            market_repo = MarketRepository(session)
            settlement_repo = SettlementRepository(session)

            assert await event_repo.get("TEST-EVENT") is not None
            assert await market_repo.get("TEST-MARKET") is not None

            settlement = await settlement_repo.get("TEST-MARKET")
            assert settlement is not None
            assert settlement.result == "yes"
            settled_at = settlement.settled_at
            if settled_at.tzinfo is None:
                settled_at = settled_at.replace(tzinfo=UTC)
            assert settled_at == api_market.settlement_ts
