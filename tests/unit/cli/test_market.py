from __future__ import annotations

import json
import re
from typing import Any

import respx
from httpx import Response
from typer.testing import CliRunner

from kalshi_research.api.models.market import Market
from kalshi_research.cli import app
from tests.unit.cli.fixtures import (
    KALSHI_PROD_BASE_URL,
    load_candlesticks_batch_fixture,
    load_events_list_fixture,
    load_market_fixture,
    load_series_candlesticks_fixture,
)

runner = CliRunner()


@respx.mock
def test_market_get() -> None:
    fixture = load_market_fixture()
    ticker = fixture["market"]["ticker"]

    respx.get(f"{KALSHI_PROD_BASE_URL}/markets/{ticker}").mock(
        return_value=Response(200, json=fixture)
    )

    market = Market.model_validate(fixture["market"])
    expected_yes = f"{market.yes_bid_cents}¢ / {market.yes_ask_cents}¢"

    result = runner.invoke(app, ["market", "get", ticker])

    assert result.exit_code == 0
    assert f"Market: {ticker}" in result.stdout
    assert market.title[:30] in result.stdout
    assert expected_yes in result.stdout
    assert "Open Time" in result.stdout
    assert "Close Time" in result.stdout


@respx.mock
def test_market_get_without_created_time() -> None:
    """Test that market get works when created_time is None."""
    fixture = load_market_fixture()
    ticker = fixture["market"]["ticker"]
    fixture["market"]["created_time"] = None

    respx.get(f"{KALSHI_PROD_BASE_URL}/markets/{ticker}").mock(
        return_value=Response(200, json=fixture)
    )

    result = runner.invoke(app, ["market", "get", ticker])

    assert result.exit_code == 0
    assert f"Market: {ticker}" in result.stdout
    assert "Open Time" in result.stdout
    assert "Close Time" in result.stdout
    # Should not show Created Time when it's None
    assert "Created Time" not in result.stdout


@respx.mock
def test_market_get_fails_when_response_missing_required_field() -> None:
    fixture = load_market_fixture()
    ticker = fixture["market"]["ticker"]

    bad_market = dict(fixture["market"])
    bad_market.pop("ticker", None)

    respx.get(f"{KALSHI_PROD_BASE_URL}/markets/{ticker}").mock(
        return_value=Response(200, json={"market": bad_market})
    )

    result = runner.invoke(app, ["market", "get", ticker])

    assert result.exit_code == 1
    assert "Error:" in result.stdout


@respx.mock
def test_market_list(make_market) -> None:
    market = make_market(ticker="TEST-MARKET", title="Test Market")
    response = {"markets": [market], "cursor": None}
    respx.get(f"{KALSHI_PROD_BASE_URL}/markets").mock(return_value=Response(200, json=response))

    result = runner.invoke(app, ["market", "list"])

    assert result.exit_code == 0
    assert "TEST-MARKET" in result.stdout
    assert "Test Market" in result.stdout


@respx.mock
def test_market_list_full_flag_disables_truncation(make_market) -> None:
    ticker_prefix = "KXTHISISAREALLYLONGTICKER-"
    ticker_suffix = "TAILTICKER"
    long_ticker = f"{ticker_prefix}{'X' * 30}{ticker_suffix}"
    assert len(long_ticker) > 30

    title_prefix = "A" * 40
    title_suffix = "TAILTITLE"
    long_title = f"{title_prefix}{title_suffix}"
    assert len(long_title) > 40

    market = make_market(ticker=long_ticker, title=long_title)
    response = {"markets": [market], "cursor": None}

    route = respx.get(f"{KALSHI_PROD_BASE_URL}/markets")
    route.side_effect = [Response(200, json=response), Response(200, json=response)]

    result_default = runner.invoke(app, ["market", "list"])
    assert result_default.exit_code == 0
    assert ticker_suffix not in result_default.stdout
    assert title_suffix not in result_default.stdout

    result_full = runner.invoke(app, ["market", "list", "--full"])
    assert result_full.exit_code == 0
    assert ticker_suffix in result_full.stdout
    assert title_suffix in result_full.stdout


@respx.mock
def test_market_list_filters_by_category(make_market) -> None:
    econ_market = make_market(ticker="ECON-MARKET", event_ticker="KXFEDRATE-26JAN")
    sports_market = make_market(ticker="SPORTS-MARKET", event_ticker="KXNFLAFCCHAMP-26JAN")

    events_fixture = load_events_list_fixture()
    template = events_fixture["events"][0]

    econ_event: dict[str, Any] = dict(template)
    econ_event.update(
        {
            "event_ticker": econ_market["event_ticker"],
            "category": "Economics",
            "title": "Economics Event",
            "markets": [econ_market],
        }
    )

    sports_event: dict[str, Any] = dict(template)
    sports_event.update(
        {
            "event_ticker": sports_market["event_ticker"],
            "category": "Sports",
            "title": "Sports Event",
            "markets": [sports_market],
        }
    )

    response = {"events": [econ_event, sports_event], "cursor": None}
    respx.get(f"{KALSHI_PROD_BASE_URL}/events").mock(return_value=Response(200, json=response))

    result = runner.invoke(app, ["market", "list", "--category", "econ"])

    assert result.exit_code == 0
    assert "ECON-MARKET" in result.stdout
    assert "SPORTS-MARKET" not in result.stdout


@respx.mock
def test_market_list_excludes_category(make_market) -> None:
    econ_market = make_market(ticker="ECON-MARKET", event_ticker="KXFEDRATE-26JAN")
    sports_market = make_market(ticker="SPORTS-MARKET", event_ticker="KXNFLAFCCHAMP-26JAN")

    events_fixture = load_events_list_fixture()
    template = events_fixture["events"][0]

    econ_event: dict[str, Any] = dict(template)
    econ_event.update(
        {
            "event_ticker": econ_market["event_ticker"],
            "category": "Economics",
            "title": "Economics Event",
            "markets": [econ_market],
        }
    )

    sports_event: dict[str, Any] = dict(template)
    sports_event.update(
        {
            "event_ticker": sports_market["event_ticker"],
            "category": "Sports",
            "title": "Sports Event",
            "markets": [sports_market],
        }
    )

    response = {"events": [econ_event, sports_event], "cursor": None}
    respx.get(f"{KALSHI_PROD_BASE_URL}/events").mock(return_value=Response(200, json=response))

    result = runner.invoke(app, ["market", "list", "--exclude-category", "sports"])

    assert result.exit_code == 0
    assert "ECON-MARKET" in result.stdout
    assert "SPORTS-MARKET" not in result.stdout


@respx.mock
def test_market_list_filters_by_event_prefix(make_market) -> None:
    fed_market = make_market(ticker="FED-MARKET", event_ticker="KXFEDRATE-26JAN")
    other_market = make_market(ticker="OTHER-MARKET", event_ticker="KXBTC-26JAN")

    events_fixture = load_events_list_fixture()
    template = events_fixture["events"][0]

    fed_event: dict[str, Any] = dict(template)
    fed_event.update(
        {
            "event_ticker": fed_market["event_ticker"],
            "category": "Economics",
            "title": "Fed Event",
            "markets": [fed_market],
        }
    )
    other_event: dict[str, Any] = dict(template)
    other_event.update(
        {
            "event_ticker": other_market["event_ticker"],
            "category": "Financials",
            "title": "Other Event",
            "markets": [other_market],
        }
    )

    response = {"events": [fed_event, other_event], "cursor": None}
    respx.get(f"{KALSHI_PROD_BASE_URL}/events").mock(return_value=Response(200, json=response))

    result = runner.invoke(app, ["market", "list", "--event-prefix", "KXFED"])

    assert result.exit_code == 0
    assert "FED-MARKET" in result.stdout
    assert "OTHER-MARKET" not in result.stdout


@respx.mock
def test_market_list_maps_active_to_open(make_market) -> None:
    response = {"markets": [make_market(ticker="TEST-MARKET")], "cursor": None}
    route = respx.get(f"{KALSHI_PROD_BASE_URL}/markets").mock(
        return_value=Response(200, json=response)
    )
    result = runner.invoke(app, ["market", "list", "--status", "active"])

    assert result.exit_code == 0
    assert "active' is a response status" in result.stdout
    assert "--status" in result.stdout
    assert "open'." in result.stdout
    assert "TEST-MARKET" in result.stdout
    assert route.call_count == 1
    assert route.calls[0].request.url.params["status"] == "open"
    assert route.calls[0].request.url.params["limit"] == "20"


def test_market_list_rejects_invalid_status() -> None:
    result = runner.invoke(app, ["market", "list", "--status", "nope"])

    assert result.exit_code == 2
    assert "Invalid status filter" in result.stdout


@respx.mock
def test_market_liquidity(make_market) -> None:
    ticker = "TEST-MARKET"
    market = make_market(
        ticker=ticker,
        volume_24h=7000,
        open_interest=3000,
    )
    orderbook = {"yes": [[47, 500]], "no": [[53, 500]]}
    respx.get(f"{KALSHI_PROD_BASE_URL}/markets/{ticker}").mock(
        return_value=Response(200, json={"market": market})
    )
    respx.get(f"{KALSHI_PROD_BASE_URL}/markets/{ticker}/orderbook").mock(
        return_value=Response(200, json={"orderbook": orderbook})
    )

    result = runner.invoke(app, ["market", "liquidity", "TEST-MARKET", "--depth", "5"])

    assert result.exit_code == 0
    assert "Liquidity Analysis" in result.stdout
    assert "Score" in result.stdout


@respx.mock
def test_market_liquidity_renders_zero_prices(make_market) -> None:
    """Ensure 0c best prices render as numbers (not treated as falsey)."""
    ticker = "TEST-MARKET"
    market = make_market(
        ticker=ticker,
        volume_24h=7000,
        open_interest=3000,
    )
    # NO bid at 100c implies a YES ask at 0c; this is a valid numeric best price.
    orderbook = {"yes": [[0, 500]], "no": [[100, 500]]}
    respx.get(f"{KALSHI_PROD_BASE_URL}/markets/{ticker}").mock(
        return_value=Response(200, json={"market": market})
    )
    respx.get(f"{KALSHI_PROD_BASE_URL}/markets/{ticker}/orderbook").mock(
        return_value=Response(200, json={"orderbook": orderbook})
    )

    result = runner.invoke(app, ["market", "liquidity", "TEST-MARKET", "--depth", "5"])

    assert result.exit_code == 0
    assert "Liquidity Analysis" in result.stdout
    assert "N/A" not in result.stdout


@respx.mock
def test_market_history_calls_get_candlesticks() -> None:
    ticker = "TEST-MARKET"
    fixture = load_candlesticks_batch_fixture()
    fixture["markets"][0]["market_ticker"] = ticker

    route = respx.get(f"{KALSHI_PROD_BASE_URL}/markets/candlesticks").mock(
        return_value=Response(200, json=fixture)
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
    close = fixture["markets"][0]["candlesticks"][0]["price"].get("close")
    if close is not None:
        assert f"{close}¢" in result.stdout

    assert route.call_count == 1
    assert route.calls[0].request.url.params["market_tickers"] == ticker
    assert int(route.calls[0].request.url.params["start_ts"]) == 1700000000
    assert int(route.calls[0].request.url.params["end_ts"]) == 1700100000
    assert int(route.calls[0].request.url.params["period_interval"]) == 60


@respx.mock
def test_market_history_with_series_uses_series_endpoint() -> None:
    ticker = "TEST-MARKET"
    series_ticker = "TEST-SERIES"
    series_fixture = load_series_candlesticks_fixture()

    series_route = respx.get(
        f"{KALSHI_PROD_BASE_URL}/series/{series_ticker}/markets/{ticker}/candlesticks"
    ).mock(return_value=Response(200, json=series_fixture))
    batch_route = respx.get(f"{KALSHI_PROD_BASE_URL}/markets/candlesticks").mock(
        return_value=Response(200, json={"markets": []})
    )

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
    assert series_route.call_count == 1
    assert batch_route.call_count == 0


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


@respx.mock
def test_market_history_no_candles_prints_message() -> None:
    respx.get(f"{KALSHI_PROD_BASE_URL}/markets/candlesticks").mock(
        return_value=Response(200, json={"markets": []})
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
    assert "No candlesticks returned" in result.stdout


@respx.mock
def test_market_history_json_output() -> None:
    ticker = "TEST-MARKET"
    fixture = load_candlesticks_batch_fixture()
    fixture["markets"][0]["market_ticker"] = ticker
    respx.get(f"{KALSHI_PROD_BASE_URL}/markets/candlesticks").mock(
        return_value=Response(200, json=fixture)
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
    stdout = result.stdout
    start_match = re.search(r"(?m)^\[", stdout)
    assert start_match is not None
    json_tail = stdout[start_match.start() :]
    payload, _ = json.JSONDecoder().raw_decode(json_tail)

    expected = fixture["markets"][0]["candlesticks"][0]
    assert payload[0]["end_period_ts"] == expected["end_period_ts"]
    assert payload[0]["price"]["close"] == expected["price"]["close"]


@respx.mock
def test_market_history_api_error_exits_with_error() -> None:
    respx.get(f"{KALSHI_PROD_BASE_URL}/markets/candlesticks").mock(
        return_value=Response(400, json={"error": "Bad request"})
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

    assert result.exit_code == 1
    assert "API Error 400" in result.stdout


@respx.mock
def test_market_history_unexpected_error_exits_with_error() -> None:
    respx.get(f"{KALSHI_PROD_BASE_URL}/markets/candlesticks").mock(side_effect=RuntimeError("boom"))

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
