from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

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
