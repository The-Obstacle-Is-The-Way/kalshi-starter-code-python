from __future__ import annotations

import json

import respx
from httpx import Response
from typer.testing import CliRunner

from kalshi_research.cli import app
from tests.unit.cli.fixtures import (
    KALSHI_PROD_BASE_URL,
    load_event_candlesticks_fixture,
    load_event_metadata_fixture,
    load_event_single_fixture,
    load_events_list_fixture,
)

runner = CliRunner()


def test_event_list_json_round_trips() -> None:
    fixture = load_events_list_fixture()
    raw_events = fixture.get("events")
    assert isinstance(raw_events, list)
    assert raw_events
    first_ticker = raw_events[0].get("event_ticker")
    assert isinstance(first_ticker, str)

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/events").mock(return_value=Response(200, json=fixture))
        result = runner.invoke(app, ["event", "list", "--limit", "5", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert payload
    assert payload[0].get("event_ticker") == first_ticker


def test_event_list_outputs_table() -> None:
    fixture = load_events_list_fixture()
    raw_events = fixture.get("events")
    assert isinstance(raw_events, list)
    assert raw_events
    first_ticker = raw_events[0].get("event_ticker")
    assert isinstance(first_ticker, str)

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/events").mock(return_value=Response(200, json=fixture))
        result = runner.invoke(app, ["event", "list", "--limit", "5"])

    assert result.exit_code == 0
    assert first_ticker in result.stdout


def test_event_list_rejects_invalid_status_exits_2() -> None:
    result = runner.invoke(app, ["event", "list", "--status", "nonsense"])

    assert result.exit_code == 2
    assert "Invalid status filter" in result.stdout


def test_event_list_active_status_warns_and_maps_to_open() -> None:
    fixture = load_events_list_fixture()

    with respx.mock:
        route = respx.get(f"{KALSHI_PROD_BASE_URL}/events").mock(
            return_value=Response(200, json=fixture)
        )
        result = runner.invoke(app, ["event", "list", "--status", "active", "--limit", "5"])

    assert result.exit_code == 0
    assert route.called
    assert "Warning" in result.stdout
    assert "status=open" in str(route.calls[0].request.url)


def test_event_list_with_markets_includes_market_count() -> None:
    fixture = load_events_list_fixture()
    raw_events = fixture.get("events")
    assert isinstance(raw_events, list)
    assert raw_events

    raw_events[0]["markets"] = []

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/events").mock(return_value=Response(200, json=fixture))
        result = runner.invoke(app, ["event", "list", "--with-markets"])

    assert result.exit_code == 0
    assert "#Markets" in result.stdout
    assert "0" in result.stdout


def test_event_list_rejects_non_positive_limit_exits_2() -> None:
    result = runner.invoke(app, ["event", "list", "--limit", "0"])

    assert result.exit_code == 2
    assert "--limit must be positive" in result.stdout


def test_event_list_api_error_exits_1() -> None:
    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/events").mock(
            return_value=Response(500, json={"error": "boom"})
        )
        result = runner.invoke(app, ["event", "list", "--limit", "5"])

    assert result.exit_code == 1
    assert "API Error 500" in result.stdout


def test_event_get_includes_metadata_when_available() -> None:
    event_fixture = load_event_single_fixture()
    metadata_fixture = load_event_metadata_fixture()
    raw_event = event_fixture.get("event")
    assert isinstance(raw_event, dict)
    ticker = raw_event.get("event_ticker")
    assert isinstance(ticker, str)

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/{ticker}").mock(
            return_value=Response(200, json=event_fixture)
        )
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/{ticker}/metadata").mock(
            return_value=Response(200, json=metadata_fixture)
        )
        result = runner.invoke(app, ["event", "get", ticker, "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload.get("event", {}).get("event_ticker") == ticker
    assert payload.get("metadata") is not None


def test_event_get_works_when_metadata_missing() -> None:
    event_fixture = load_event_single_fixture()
    raw_event = event_fixture.get("event")
    assert isinstance(raw_event, dict)
    ticker = raw_event.get("event_ticker")
    assert isinstance(ticker, str)

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/{ticker}").mock(
            return_value=Response(200, json=event_fixture)
        )
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/{ticker}/metadata").mock(
            return_value=Response(404, json={"error": "not found"})
        )
        result = runner.invoke(app, ["event", "get", ticker, "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload.get("event", {}).get("event_ticker") == ticker
    assert payload.get("metadata") is None


def test_event_get_outputs_tables() -> None:
    event_fixture = load_event_single_fixture()
    metadata_fixture = load_event_metadata_fixture()
    raw_event = event_fixture.get("event")
    assert isinstance(raw_event, dict)
    ticker = raw_event.get("event_ticker")
    assert isinstance(ticker, str)

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/{ticker}").mock(
            return_value=Response(200, json=event_fixture)
        )
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/{ticker}/metadata").mock(
            return_value=Response(200, json=metadata_fixture)
        )
        result = runner.invoke(app, ["event", "get", ticker])

    assert result.exit_code == 0
    assert ticker in result.stdout
    assert "Event Metadata" in result.stdout
    assert "Market Metadata" in result.stdout


def test_event_get_warns_when_metadata_missing_in_human_mode() -> None:
    event_fixture = load_event_single_fixture()
    raw_event = event_fixture.get("event")
    assert isinstance(raw_event, dict)
    ticker = raw_event.get("event_ticker")
    assert isinstance(ticker, str)

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/{ticker}").mock(
            return_value=Response(200, json=event_fixture)
        )
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/{ticker}/metadata").mock(
            return_value=Response(404, json={"error": "not found"})
        )
        result = runner.invoke(app, ["event", "get", ticker])

    assert result.exit_code == 0
    assert "Warning" in result.stdout


def test_event_get_warns_when_metadata_invalid_json() -> None:
    event_fixture = load_event_single_fixture()
    raw_event = event_fixture.get("event")
    assert isinstance(raw_event, dict)
    ticker = raw_event.get("event_ticker")
    assert isinstance(ticker, str)

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/{ticker}").mock(
            return_value=Response(200, json=event_fixture)
        )
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/{ticker}/metadata").mock(
            return_value=Response(200, text="not-json")
        )
        result = runner.invoke(app, ["event", "get", ticker])

    assert result.exit_code == 0
    assert "Warning" in result.stdout


def test_event_candlesticks_derives_series_ticker() -> None:
    event_fixture = load_event_single_fixture()
    candles_fixture = load_event_candlesticks_fixture()
    raw_event = event_fixture.get("event")
    assert isinstance(raw_event, dict)
    ticker = raw_event.get("event_ticker")
    assert isinstance(ticker, str)
    series_ticker = raw_event.get("series_ticker")
    assert isinstance(series_ticker, str)

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/{ticker}").mock(
            return_value=Response(200, json=event_fixture)
        )
        respx.get(
            f"{KALSHI_PROD_BASE_URL}/series/{series_ticker}/events/{ticker}/candlesticks"
        ).mock(return_value=Response(200, json=candles_fixture))
        result = runner.invoke(app, ["event", "candlesticks", ticker, "--days", "1", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload.get("series_ticker") == series_ticker
    assert payload.get("market_tickers") == candles_fixture.get("market_tickers")


def test_event_candlesticks_outputs_table() -> None:
    event_fixture = load_event_single_fixture()
    candles_fixture = load_event_candlesticks_fixture()
    raw_event = event_fixture.get("event")
    assert isinstance(raw_event, dict)
    ticker = raw_event.get("event_ticker")
    assert isinstance(ticker, str)
    series_ticker = raw_event.get("series_ticker")
    assert isinstance(series_ticker, str)

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/{ticker}").mock(
            return_value=Response(200, json=event_fixture)
        )
        respx.get(
            f"{KALSHI_PROD_BASE_URL}/series/{series_ticker}/events/{ticker}/candlesticks"
        ).mock(return_value=Response(200, json=candles_fixture))
        result = runner.invoke(app, ["event", "candlesticks", ticker, "--days", "1"])

    assert result.exit_code == 0
    assert "Event Candlesticks" in result.stdout
    assert series_ticker in result.stdout


def test_event_candlesticks_rejects_invalid_interval_exits_2() -> None:
    result = runner.invoke(app, ["event", "candlesticks", "EVT", "--interval", "2h"])

    assert result.exit_code == 2
    assert "Invalid interval" in result.stdout


def test_event_candlesticks_rejects_invalid_time_window_exits_2() -> None:
    result = runner.invoke(
        app,
        ["event", "candlesticks", "EVT", "--start-ts", "10", "--end-ts", "10"],
    )

    assert result.exit_code == 2
    assert "start-ts must be < end-ts" in result.stdout


def test_event_candlesticks_rejects_days_zero_exits_2() -> None:
    result = runner.invoke(app, ["event", "candlesticks", "EVT", "--days", "0"])

    assert result.exit_code == 2
    assert "--days must be > 0" in result.stdout
