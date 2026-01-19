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
