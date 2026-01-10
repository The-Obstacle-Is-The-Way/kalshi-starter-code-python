from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from kalshi_research.api.models.orderbook import Orderbook
from kalshi_research.cli import app

runner = CliRunner()


@patch("kalshi_research.api.KalshiPublicClient")
def test_market_get(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    mock_market = MagicMock()
    mock_market.ticker = "TEST-MARKET"
    mock_market.title = "Test Market"
    mock_market.event_ticker = "TEST-EVENT"
    mock_market.status.value = "active"
    mock_market.yes_bid_cents = 50
    mock_market.yes_ask_cents = 52
    mock_market.no_bid_cents = 48
    mock_market.no_ask_cents = 50
    mock_market.volume_24h = 1000
    mock_market.open_interest = 500
    mock_market.open_time.isoformat.return_value = "2024-01-01T00:00:00"
    mock_market.created_time = MagicMock()
    mock_market.created_time.isoformat.return_value = "2023-12-15T17:50:26"
    mock_market.close_time.isoformat.return_value = "2025-01-01T00:00:00"

    mock_client.get_market.return_value = mock_market

    result = runner.invoke(app, ["market", "get", "TEST-MARKET"])

    assert result.exit_code == 0
    assert "Market: TEST-MARKET" in result.stdout
    assert "Test Market" in result.stdout
    assert "50¢ / 52¢" in result.stdout
    assert "Open Time" in result.stdout
    assert "Created Time" in result.stdout
    assert "Close Time" in result.stdout


@patch("kalshi_research.api.KalshiPublicClient")
def test_market_get_without_created_time(mock_client_cls: MagicMock) -> None:
    """Test that market get works when created_time is None."""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    mock_market = MagicMock()
    mock_market.ticker = "TEST-MARKET"
    mock_market.title = "Test Market"
    mock_market.event_ticker = "TEST-EVENT"
    mock_market.status.value = "active"
    mock_market.yes_bid_cents = 50
    mock_market.yes_ask_cents = 52
    mock_market.no_bid_cents = 48
    mock_market.no_ask_cents = 50
    mock_market.volume_24h = 1000
    mock_market.open_interest = 500
    mock_market.open_time.isoformat.return_value = "2024-01-01T00:00:00"
    mock_market.created_time = None
    mock_market.close_time.isoformat.return_value = "2025-01-01T00:00:00"

    mock_client.get_market.return_value = mock_market

    result = runner.invoke(app, ["market", "get", "TEST-MARKET"])

    assert result.exit_code == 0
    assert "Market: TEST-MARKET" in result.stdout
    assert "Open Time" in result.stdout
    assert "Close Time" in result.stdout
    # Should not show Created Time when it's None
    assert "Created Time" not in result.stdout


@patch("kalshi_research.api.KalshiPublicClient")
def test_market_list(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    mock_market = MagicMock()
    mock_market.ticker = "TEST-MARKET"
    mock_market.title = "Test Market"
    mock_market.status.value = "active"
    mock_market.yes_bid_cents = 50
    mock_market.volume_24h = 1000

    mock_client.get_markets.return_value = [mock_market]

    result = runner.invoke(app, ["market", "list"])

    assert result.exit_code == 0
    assert "TEST-MARKET" in result.stdout
    assert "Test Market" in result.stdout


@patch("kalshi_research.api.KalshiPublicClient")
def test_market_liquidity(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    mock_market = MagicMock()
    mock_market.volume_24h = 7000
    mock_market.open_interest = 3000
    mock_client.get_market.return_value = mock_market

    mock_client.get_orderbook.return_value = Orderbook(yes=[(47, 500)], no=[(53, 500)])

    result = runner.invoke(app, ["market", "liquidity", "TEST-MARKET", "--depth", "5"])

    assert result.exit_code == 0
    assert "Liquidity Analysis" in result.stdout
    assert "Score" in result.stdout
