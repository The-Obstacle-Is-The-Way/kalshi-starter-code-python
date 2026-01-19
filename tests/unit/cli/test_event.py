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
