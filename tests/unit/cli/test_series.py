from __future__ import annotations

import json

import respx
from httpx import Response
from typer.testing import CliRunner

from kalshi_research.cli import app
from tests.unit.cli.fixtures import KALSHI_PROD_BASE_URL, load_series_single_fixture

runner = CliRunner()


def test_series_get_json_round_trips() -> None:
    fixture = load_series_single_fixture()
    raw = fixture.get("series")
    assert isinstance(raw, dict)
    ticker = raw.get("ticker")
    assert isinstance(ticker, str)

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/series/{ticker}").mock(
            return_value=Response(200, json=fixture)
        )
        result = runner.invoke(app, ["series", "get", ticker, "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload.get("ticker") == ticker


def test_series_get_outputs_table() -> None:
    fixture = load_series_single_fixture()
    raw = fixture.get("series")
    assert isinstance(raw, dict)
    ticker = raw.get("ticker")
    assert isinstance(ticker, str)
    raw["volume"] = 12_345
    sources = raw.get("settlement_sources")
    assert isinstance(sources, list)
    raw["settlement_sources"] = sources * 12

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/series/{ticker}").mock(
            return_value=Response(200, json=fixture)
        )
        result = runner.invoke(app, ["series", "get", ticker])

    assert result.exit_code == 0
    assert f"Series: {ticker}" in result.stdout
    assert "Volume" in result.stdout
    assert "12,345" in result.stdout
    assert "Settlement Sources" in result.stdout
    assert "… (+9)" in result.stdout


def test_series_get_404_exits_2() -> None:
    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/series/MISSING").mock(
            return_value=Response(404, json={"error": "not found"})
        )
        result = runner.invoke(app, ["series", "get", "MISSING"])

    assert result.exit_code == 2
    assert "API Error 404" in result.stdout


def test_series_get_invalid_json_exits_1() -> None:
    fixture = load_series_single_fixture()
    raw = fixture.get("series")
    assert isinstance(raw, dict)
    ticker = raw.get("ticker")
    assert isinstance(ticker, str)

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/series/{ticker}").mock(
            return_value=Response(200, text="not-json")
        )
        result = runner.invoke(app, ["series", "get", ticker])

    assert result.exit_code == 1
    assert "Invalid JSON response" in result.stdout
