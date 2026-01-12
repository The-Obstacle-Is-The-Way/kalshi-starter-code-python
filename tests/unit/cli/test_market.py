from __future__ import annotations

import json
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
def test_market_list_full_flag_disables_truncation(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    ticker_prefix = "KXTHISISAREALLYLONGTICKER-"
    ticker_suffix = "TAILTICKER"
    long_ticker = f"{ticker_prefix}{'X' * 30}{ticker_suffix}"
    assert len(long_ticker) > 30

    title_prefix = "A" * 40
    title_suffix = "TAILTITLE"
    long_title = f"{title_prefix}{title_suffix}"
    assert len(long_title) > 40

    mock_market = MagicMock()
    mock_market.ticker = long_ticker
    mock_market.title = long_title
    mock_market.status.value = "active"
    mock_market.yes_bid_cents = 50
    mock_market.volume_24h = 1000

    mock_client.get_markets.return_value = [mock_market]

    result_default = runner.invoke(app, ["market", "list"])
    assert result_default.exit_code == 0
    assert ticker_suffix not in result_default.stdout
    assert title_suffix not in result_default.stdout

    result_full = runner.invoke(app, ["market", "list", "--full"])
    assert result_full.exit_code == 0
    assert ticker_suffix in result_full.stdout
    assert title_suffix in result_full.stdout


@patch("kalshi_research.api.KalshiPublicClient")
def test_market_list_filters_by_category(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    econ_market = MagicMock()
    econ_market.ticker = "ECON-MARKET"
    econ_market.event_ticker = "KXFEDRATE-26JAN"
    econ_market.title = "Economics Market"
    econ_market.status.value = "active"
    econ_market.yes_bid_cents = 50
    econ_market.volume_24h = 1000

    sports_market = MagicMock()
    sports_market.ticker = "SPORTS-MARKET"
    sports_market.event_ticker = "KXNFLAFCCHAMP-26JAN"
    sports_market.title = "Sports Market"
    sports_market.status.value = "active"
    sports_market.yes_bid_cents = 50
    sports_market.volume_24h = 1000

    econ_event = MagicMock()
    econ_event.event_ticker = econ_market.event_ticker
    econ_event.category = "Economics"
    econ_event.markets = [econ_market]

    sports_event = MagicMock()
    sports_event.event_ticker = sports_market.event_ticker
    sports_event.category = "Sports"
    sports_event.markets = [sports_market]

    async def event_gen(*args: object, **kwargs: object):
        _ = args, kwargs
        yield econ_event
        yield sports_event

    mock_client.get_all_events = MagicMock(side_effect=event_gen)

    result = runner.invoke(app, ["market", "list", "--category", "econ"])

    assert result.exit_code == 0
    assert "ECON-MARKET" in result.stdout
    assert "SPORTS-MARKET" not in result.stdout


@patch("kalshi_research.api.KalshiPublicClient")
def test_market_list_excludes_category(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    econ_market = MagicMock()
    econ_market.ticker = "ECON-MARKET"
    econ_market.event_ticker = "KXFEDRATE-26JAN"
    econ_market.title = "Economics Market"
    econ_market.status.value = "active"
    econ_market.yes_bid_cents = 50
    econ_market.volume_24h = 1000

    sports_market = MagicMock()
    sports_market.ticker = "SPORTS-MARKET"
    sports_market.event_ticker = "KXNFLAFCCHAMP-26JAN"
    sports_market.title = "Sports Market"
    sports_market.status.value = "active"
    sports_market.yes_bid_cents = 50
    sports_market.volume_24h = 1000

    econ_event = MagicMock()
    econ_event.event_ticker = econ_market.event_ticker
    econ_event.category = "Economics"
    econ_event.markets = [econ_market]

    sports_event = MagicMock()
    sports_event.event_ticker = sports_market.event_ticker
    sports_event.category = "Sports"
    sports_event.markets = [sports_market]

    async def event_gen(*args: object, **kwargs: object):
        _ = args, kwargs
        yield econ_event
        yield sports_event

    mock_client.get_all_events = MagicMock(side_effect=event_gen)

    result = runner.invoke(app, ["market", "list", "--exclude-category", "sports"])

    assert result.exit_code == 0
    assert "ECON-MARKET" in result.stdout
    assert "SPORTS-MARKET" not in result.stdout


@patch("kalshi_research.api.KalshiPublicClient")
def test_market_list_filters_by_event_prefix(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    fed_market = MagicMock()
    fed_market.ticker = "FED-MARKET"
    fed_market.event_ticker = "KXFEDRATE-26JAN"
    fed_market.title = "Fed Market"
    fed_market.status.value = "active"
    fed_market.yes_bid_cents = 50
    fed_market.volume_24h = 1000

    other_market = MagicMock()
    other_market.ticker = "OTHER-MARKET"
    other_market.event_ticker = "KXBTC-26JAN"
    other_market.title = "Other Market"
    other_market.status.value = "active"
    other_market.yes_bid_cents = 50
    other_market.volume_24h = 1000

    fed_event = MagicMock()
    fed_event.event_ticker = fed_market.event_ticker
    fed_event.category = "Economics"
    fed_event.markets = [fed_market]

    other_event = MagicMock()
    other_event.event_ticker = other_market.event_ticker
    other_event.category = "Financials"
    other_event.markets = [other_market]

    async def event_gen(*args: object, **kwargs: object):
        _ = args, kwargs
        yield fed_event
        yield other_event

    mock_client.get_all_events = MagicMock(side_effect=event_gen)

    result = runner.invoke(app, ["market", "list", "--event-prefix", "KXFED"])

    assert result.exit_code == 0
    assert "FED-MARKET" in result.stdout
    assert "OTHER-MARKET" not in result.stdout


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


def test_market_history_rejects_invalid_interval() -> None:
    result = runner.invoke(
        app,
        [
            "market",
            "history",
            "TEST-MARKET",
            "--interval",
            "2h",
            "--start-ts",
            "1700000000",
            "--end-ts",
            "1700100000",
        ],
    )

    assert result.exit_code == 2
    assert "Invalid interval" in result.stdout


def test_market_history_rejects_days_when_start_ts_missing() -> None:
    result = runner.invoke(
        app,
        [
            "market",
            "history",
            "TEST-MARKET",
            "--interval",
            "1h",
            "--days",
            "0",
            "--end-ts",
            "1700100000",
        ],
    )

    assert result.exit_code == 2
    assert "--days must be > 0" in result.stdout


def test_market_history_rejects_start_ts_after_end_ts() -> None:
    result = runner.invoke(
        app,
        [
            "market",
            "history",
            "TEST-MARKET",
            "--interval",
            "1h",
            "--start-ts",
            "200",
            "--end-ts",
            "100",
        ],
    )

    assert result.exit_code == 2
    assert "start-ts must be < end-ts" in result.stdout


@patch("kalshi_research.api.KalshiPublicClient")
def test_market_history_no_candles_prints_message(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    mock_client.get_candlesticks = AsyncMock(return_value=[])

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
    assert "No candlesticks returned" in result.stdout


@patch("kalshi_research.api.KalshiPublicClient")
def test_market_history_json_output(mock_client_cls: MagicMock) -> None:
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
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload[0]["end_period_ts"] == 1700003600
    assert payload[0]["price"]["close"] == 47


@patch("kalshi_research.api.KalshiPublicClient")
def test_market_history_api_error_exits_with_error(mock_client_cls: MagicMock) -> None:
    from kalshi_research.api.exceptions import KalshiAPIError

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    mock_client.get_candlesticks = AsyncMock(side_effect=KalshiAPIError(400, "Bad request"))

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

    assert result.exit_code == 1
    assert "API Error 400" in result.stdout


@patch("kalshi_research.api.KalshiPublicClient")
def test_market_history_unexpected_error_exits_with_error(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    mock_client.get_candlesticks = AsyncMock(side_effect=RuntimeError("boom"))

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

    assert result.exit_code == 1
    assert "boom" in result.stdout
