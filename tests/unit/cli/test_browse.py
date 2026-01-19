from __future__ import annotations

import json

import respx
from httpx import Response
from typer.testing import CliRunner

from kalshi_research.cli import app
from tests.unit.cli.fixtures import (
    KALSHI_PROD_BASE_URL,
    load_filters_by_sport_fixture,
    load_series_list_fixture,
    load_tags_by_categories_fixture,
)

runner = CliRunner()


def test_browse_categories_outputs_categories() -> None:
    fixture = load_tags_by_categories_fixture()
    tags_by_categories = fixture.get("tags_by_categories")
    assert isinstance(tags_by_categories, dict)
    category = next(iter(tags_by_categories.keys()))

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/search/tags_by_categories").mock(
            return_value=Response(200, json=fixture)
        )
        result = runner.invoke(app, ["browse", "categories"])

    assert result.exit_code == 0
    assert category in result.stdout


def test_browse_categories_json_round_trips() -> None:
    fixture = load_tags_by_categories_fixture()
    tags_by_categories = fixture.get("tags_by_categories")
    assert isinstance(tags_by_categories, dict)
    category = next(iter(tags_by_categories.keys()))

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/search/tags_by_categories").mock(
            return_value=Response(200, json=fixture)
        )
        result = runner.invoke(app, ["browse", "categories", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    assert category in payload


def test_browse_series_outputs_tickers() -> None:
    fixture = load_series_list_fixture()
    raw_series = fixture.get("series")
    assert isinstance(raw_series, list)
    assert raw_series
    first_ticker = raw_series[0].get("ticker")
    assert isinstance(first_ticker, str)

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/series").mock(return_value=Response(200, json=fixture))
        result = runner.invoke(app, ["browse", "series"])

    assert result.exit_code == 0
    assert first_ticker in result.stdout


def test_browse_series_json_round_trips() -> None:
    fixture = load_series_list_fixture()
    raw_series = fixture.get("series")
    assert isinstance(raw_series, list)
    assert raw_series
    first_ticker = raw_series[0].get("ticker")
    assert isinstance(first_ticker, str)

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/series").mock(return_value=Response(200, json=fixture))
        result = runner.invoke(app, ["browse", "series", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert payload
    assert payload[0].get("ticker") == first_ticker


def test_browse_sports_json_round_trips() -> None:
    fixture = load_filters_by_sport_fixture()

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/search/filters_by_sport").mock(
            return_value=Response(200, json=fixture)
        )
        result = runner.invoke(app, ["browse", "sports", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    assert payload.get("sport_ordering") == fixture.get("sport_ordering")
