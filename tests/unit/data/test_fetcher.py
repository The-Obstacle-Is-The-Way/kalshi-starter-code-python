from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kalshi_research.api.models.event import Event
from kalshi_research.api.models.market import Market, MarketStatus
from kalshi_research.data.fetcher import DataFetcher


@pytest.fixture
def mock_db():
    db = MagicMock()
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    db.session_factory.return_value = session
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


@pytest.mark.asyncio
async def test_sync_events(data_fetcher, mock_client, mock_db):
    # Mock API events
    mock_event = MagicMock(spec=Event)
    mock_event.event_ticker = "TEST-EVENT"
    mock_event.series_ticker = "TEST-SERIES"
    mock_event.title = "Test Event"
    mock_event.category = "Test"

    mock_client.get_events.return_value = [mock_event]

    # Mock repository
    with patch("kalshi_research.data.fetcher.EventRepository") as MockRepo:
        mock_repo = AsyncMock()
        MockRepo.return_value = mock_repo

        count = await data_fetcher.sync_events()

        assert count == 1
        mock_repo.upsert.assert_called_once()
        mock_repo.commit.assert_called_once()


@pytest.mark.asyncio
async def test_sync_markets(data_fetcher, mock_client, mock_db):
    # Mock API markets
    mock_market = MagicMock(spec=Market)
    mock_market.ticker = "TEST-MARKET"
    mock_market.event_ticker = "TEST-EVENT"
    mock_market.series_ticker = "TEST-SERIES"
    mock_market.title = "Test Market"
    mock_market.subtitle = "Subtitle"
    mock_market.status = MarketStatus.ACTIVE
    mock_market.result = ""
    mock_market.open_time = "2024-01-01T00:00:00Z"
    mock_market.close_time = "2025-01-01T00:00:00Z"
    mock_market.expiration_time = "2025-01-01T00:00:00Z"

    # Correctly mock async generator
    async def market_gen(status=None):
        yield mock_market

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
        event_repo.get.return_value = MagicMock()  # Event exists
        MockEventRepo.return_value = event_repo

        count = await data_fetcher.sync_markets()

        assert count == 1
        market_repo.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_take_snapshot(data_fetcher, mock_client, mock_db):
    mock_market = MagicMock(spec=Market)
    mock_market.ticker = "TEST-MARKET"
    mock_market.yes_bid = 50
    mock_market.yes_ask = 52
    mock_market.no_bid = 48
    mock_market.no_ask = 50
    mock_market.last_price = 51
    mock_market.volume = 1000
    mock_market.volume_24h = 100
    mock_market.open_interest = 500
    mock_market.liquidity = 10000

    async def market_gen(status=None):
        yield mock_market

    mock_client.get_all_markets = MagicMock(side_effect=market_gen)

    with patch("kalshi_research.data.fetcher.PriceRepository") as MockPriceRepo:
        repo = AsyncMock()
        MockPriceRepo.return_value = repo

        count = await data_fetcher.take_snapshot()

        assert count == 1
        repo.add.assert_called_once()
        # The fetcher calls session.commit(), not repo.commit()
        mock_db.session_factory.return_value.commit.assert_called()


@pytest.mark.asyncio
async def test_full_sync(data_fetcher):
    data_fetcher.sync_events = AsyncMock(return_value=5)
    data_fetcher.sync_markets = AsyncMock(return_value=10)
    data_fetcher.take_snapshot = AsyncMock(return_value=100)

    result = await data_fetcher.full_sync()

    assert result["events"] == 5
    assert result["markets"] == 10
    assert result["snapshots"] == 100
