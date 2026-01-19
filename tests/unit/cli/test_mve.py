from __future__ import annotations

import json

import respx
from httpx import Response
from typer.testing import CliRunner

from kalshi_research.cli import app
from tests.unit.cli.fixtures import (
    KALSHI_PROD_BASE_URL,
    load_multivariate_event_collection_fixture,
    load_multivariate_event_collections_fixture,
    load_multivariate_events_fixture,
)

runner = CliRunner()


def test_mve_list_json_round_trips() -> None:
    fixture = load_multivariate_events_fixture()
    raw_events = fixture.get("events")
    assert isinstance(raw_events, list)
    assert raw_events
    first_ticker = raw_events[0].get("event_ticker")
    assert isinstance(first_ticker, str)

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/multivariate").mock(
            return_value=Response(200, json=fixture)
        )
        result = runner.invoke(app, ["mve", "list", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert payload
    assert payload[0].get("event_ticker") == first_ticker


def test_mve_collections_json_round_trips() -> None:
    fixture = load_multivariate_event_collections_fixture()
    raw = fixture.get("multivariate_contracts")
    assert isinstance(raw, list)
    assert raw
    ticker = raw[0].get("collection_ticker")
    assert isinstance(ticker, str)

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/multivariate_event_collections").mock(
            return_value=Response(200, json=fixture)
        )
        result = runner.invoke(app, ["mve", "collections", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    contracts = payload.get("multivariate_contracts")
    assert isinstance(contracts, list)
    assert contracts
    assert contracts[0].get("collection_ticker") == ticker


def test_mve_collection_json_round_trips() -> None:
    fixture = load_multivariate_event_collection_fixture()
    raw = fixture.get("multivariate_contract")
    assert isinstance(raw, dict)
    ticker = raw.get("collection_ticker")
    assert isinstance(ticker, str)

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/multivariate_event_collections/{ticker}").mock(
            return_value=Response(200, json=fixture)
        )
        result = runner.invoke(app, ["mve", "collection", ticker, "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload.get("collection_ticker") == ticker
