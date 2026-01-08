from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from kalshi_research.cli import app

runner = CliRunner()


def test_version() -> None:
    """Test the version command."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "kalshi-research v0.1.0" in result.stdout


@patch("kalshi_research.api.KalshiPublicClient")
def test_market_get(mock_client_cls: MagicMock) -> None:
    """Test getting a market."""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    # Mock market data
    mock_market = MagicMock()
    mock_market.ticker = "TEST-MARKET"
    mock_market.title = "Test Market"
    mock_market.event_ticker = "TEST-EVENT"
    mock_market.status.value = "active"
    mock_market.yes_bid = 50
    mock_market.yes_ask = 52
    mock_market.no_bid = 48
    mock_market.no_ask = 50
    mock_market.volume_24h = 1000
    mock_market.open_interest = 500
    mock_market.close_time.isoformat.return_value = "2025-01-01T00:00:00"

    mock_client.get_market.return_value = mock_market

    result = runner.invoke(app, ["market", "get", "TEST-MARKET"])

    assert result.exit_code == 0
    assert "Market: TEST-MARKET" in result.stdout
    assert "Test Market" in result.stdout
    assert "50¢ / 52¢" in result.stdout


@patch("kalshi_research.api.KalshiPublicClient")
def test_market_list(mock_client_cls: MagicMock) -> None:
    """Test listing markets."""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    mock_market = MagicMock()
    mock_market.ticker = "TEST-MARKET"
    mock_market.title = "Test Market"
    mock_market.status.value = "active"
    mock_market.yes_bid = 50
    mock_market.volume_24h = 1000

    mock_client.get_markets.return_value = [mock_market]

    result = runner.invoke(app, ["market", "list"])

    assert result.exit_code == 0
    assert "TEST-MARKET" in result.stdout
    assert "Test Market" in result.stdout


@patch("kalshi_research.data.DatabaseManager")
def test_data_init(mock_db_cls: MagicMock) -> None:
    """Test initializing the database."""
    mock_db = MagicMock()
    mock_db.create_tables = AsyncMock()
    mock_db.close = AsyncMock()
    mock_db_cls.return_value = mock_db

    result = runner.invoke(app, ["data", "init"])

    assert result.exit_code == 0
    assert "Database initialized" in result.stdout
    mock_db.create_tables.assert_called_once()


@patch("kalshi_research.data.DataFetcher")
@patch("kalshi_research.data.DatabaseManager")
def test_data_sync_markets(mock_db_cls: MagicMock, mock_fetcher_cls: MagicMock) -> None:
    """Test syncing markets."""
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    mock_db_cls.return_value = mock_db

    mock_fetcher = AsyncMock()
    mock_fetcher.__aenter__.return_value = mock_fetcher
    mock_fetcher.__aexit__.return_value = None
    mock_fetcher.sync_events.return_value = 5
    mock_fetcher.sync_markets.return_value = 10
    mock_fetcher_cls.return_value = mock_fetcher

    result = runner.invoke(app, ["data", "sync-markets"])

    assert result.exit_code == 0
    # Relaxed assertion to handle rich formatting nuances
    assert "5 events" in result.stdout
    assert "10 markets" in result.stdout


@patch("kalshi_research.data.DataFetcher")
@patch("kalshi_research.data.DatabaseManager")
def test_data_sync_settlements(mock_db_cls: MagicMock, mock_fetcher_cls: MagicMock) -> None:
    """Test syncing settlements."""
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    mock_db_cls.return_value = mock_db

    mock_fetcher = AsyncMock()
    mock_fetcher.__aenter__.return_value = mock_fetcher
    mock_fetcher.__aexit__.return_value = None
    mock_fetcher.sync_settlements.return_value = 123
    mock_fetcher_cls.return_value = mock_fetcher

    result = runner.invoke(app, ["data", "sync-settlements"])

    assert result.exit_code == 0
    assert "123 settlements" in result.stdout
    mock_fetcher.sync_settlements.assert_called_once_with(max_pages=None)


@patch("kalshi_research.data.DataFetcher")
@patch("kalshi_research.data.DatabaseManager")
def test_data_snapshot(mock_db_cls: MagicMock, mock_fetcher_cls: MagicMock) -> None:
    """Test taking a snapshot."""
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    mock_db_cls.return_value = mock_db

    mock_fetcher = AsyncMock()
    mock_fetcher.__aenter__.return_value = mock_fetcher
    mock_fetcher.__aexit__.return_value = None
    mock_fetcher.take_snapshot.return_value = 100
    mock_fetcher_cls.return_value = mock_fetcher

    result = runner.invoke(app, ["data", "snapshot"])

    assert result.exit_code == 0
    assert "Took 100 price snapshots" in result.stdout


@patch("kalshi_research.data.export.export_to_parquet")
def test_data_export(mock_export: MagicMock) -> None:
    """Test data export."""
    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["data", "export", "--format", "parquet"])

    assert result.exit_code == 0
    assert "Exported to" in result.stdout
    mock_export.assert_called_once()


@patch("kalshi_research.data.DatabaseManager")
@patch("kalshi_research.data.repositories.EventRepository")
@patch("kalshi_research.data.repositories.MarketRepository")
@patch("kalshi_research.data.repositories.PriceRepository")
def test_data_stats(
    mock_price_repo: MagicMock,
    mock_market_repo: MagicMock,
    mock_event_repo: MagicMock,
    mock_db_cls: MagicMock,
) -> None:
    """Test database stats."""
    # Mock db path existence
    with patch("pathlib.Path.exists", return_value=True):
        mock_db = MagicMock()  # Changed from AsyncMock to MagicMock for the manager itself
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # session_factory property returns the callable/object that is context manager
        # If accessing property:
        mock_db.session_factory.return_value = mock_session
        # But wait, cli uses: async with db.session_factory() as session
        # So db.session_factory must be a callable that returns the context manager

        mock_db_cls.return_value = mock_db

        mock_event_repo.return_value.get_all = AsyncMock(return_value=[1, 2, 3])
        mock_market_repo.return_value.get_all = AsyncMock(return_value=[1, 2])
        mock_market_repo.return_value.count_by_status = AsyncMock(return_value={"active": 2})

        mock_market = MagicMock()
        mock_market.ticker = "TEST"
        mock_market_repo.return_value.get_active = AsyncMock(return_value=[mock_market])
        mock_price_repo.return_value.count_for_market = AsyncMock(return_value=10)

        result = runner.invoke(app, ["data", "stats"])

    assert result.exit_code == 0
    assert "Total Events" in result.stdout
    assert "3" in result.stdout
