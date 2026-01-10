from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from kalshi_research.api.models.candlestick import (
    CandlePrice,
    CandleSide,
    Candlestick,
    CandlestickResponse,
)
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
def test_market_list_maps_active_to_open(mock_client_cls: MagicMock) -> None:
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

    result = runner.invoke(app, ["market", "list", "--status", "active"])

    assert result.exit_code == 0
    assert "active' is a response status" in result.stdout
    assert "--status" in result.stdout
    assert "open'." in result.stdout
    assert "TEST-MARKET" in result.stdout
    mock_client.get_markets.assert_awaited_once_with(status="open", event_ticker=None, limit=20)


@patch("kalshi_research.api.KalshiPublicClient")
def test_market_list_rejects_invalid_status(mock_client_cls: MagicMock) -> None:
    result = runner.invoke(app, ["market", "list", "--status", "nope"])

    assert result.exit_code == 2
    assert "Invalid status filter" in result.stdout
    mock_client_cls.assert_not_called()


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


@patch("kalshi_research.api.KalshiPublicClient")
def test_market_liquidity_renders_zero_prices(mock_client_cls: MagicMock) -> None:
    """Ensure 0c best prices render as numbers (not treated as falsey)."""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    mock_market = MagicMock()
    mock_market.volume_24h = 7000
    mock_market.open_interest = 3000
    mock_client.get_market.return_value = mock_market

    # NO bid at 100c implies a YES ask at 0c; this is a valid numeric best price.
    mock_client.get_orderbook.return_value = Orderbook(yes=[(0, 500)], no=[(100, 500)])

    result = runner.invoke(app, ["market", "liquidity", "TEST-MARKET", "--depth", "5"])

    assert result.exit_code == 0
    assert "Liquidity Analysis" in result.stdout
    assert "N/A" not in result.stdout


@patch("kalshi_research.api.KalshiPublicClient")
def test_market_history_calls_get_candlesticks(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    mock_client.get_candlesticks = AsyncMock(
        return_value=[
            CandlestickResponse(
                market_ticker="TEST-MARKET",
                candlesticks=[
                    Candlestick(
                        end_period_ts=1700003600,
                        open_interest=123,
                        volume=1000,
                        price=CandlePrice(close=47),
                        yes_bid=CandleSide(),
                        yes_ask=CandleSide(),
                    )
                ],
            )
        ]
    )

    result = runner.invoke(
        app,
        [
            "market",
            "history",
            "TEST-MARKET",
            "--interval",
            "1h",
            "--start-ts",
            "1700000000",
            "--end-ts",
            "1700100000",
        ],
    )

    assert result.exit_code == 0
    assert "Candlestick History: TEST-MARKET" in result.stdout
    assert "47¢" in result.stdout
    mock_client.get_candlesticks.assert_awaited_once_with(
        market_tickers=["TEST-MARKET"],
        start_ts=1700000000,
        end_ts=1700100000,
        period_interval=60,
    )


@patch("kalshi_research.api.KalshiPublicClient")
def test_market_history_with_series_uses_series_endpoint(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    mock_client.get_series_candlesticks = AsyncMock(
        return_value=[
            Candlestick(
                end_period_ts=1700003600,
                open_interest=123,
                volume=1000,
                price=CandlePrice(close=47),
                yes_bid=CandleSide(),
                yes_ask=CandleSide(),
            )
        ]
    )
    mock_client.get_candlesticks = AsyncMock()

    result = runner.invoke(
        app,
        [
            "market",
            "history",
            "TEST-MARKET",
            "--series",
            "TEST-SERIES",
            "--interval",
            "1h",
            "--start-ts",
            "1700000000",
            "--end-ts",
            "1700100000",
        ],
    )

    assert result.exit_code == 0
    assert "Candlestick History: TEST-MARKET" in result.stdout
    mock_client.get_series_candlesticks.assert_awaited_once_with(
        series_ticker="TEST-SERIES",
        ticker="TEST-MARKET",
        start_ts=1700000000,
        end_ts=1700100000,
        period_interval=60,
    )
    mock_client.get_candlesticks.assert_not_awaited()
