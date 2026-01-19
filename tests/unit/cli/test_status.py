from __future__ import annotations

import json

import respx
from httpx import Response
from typer.testing import CliRunner

from kalshi_research.cli import app
from tests.unit.cli.fixtures import (
    KALSHI_PROD_BASE_URL,
    load_exchange_announcements_fixture,
    load_exchange_schedule_fixture,
    load_exchange_status_fixture,
)

runner = CliRunner()


def test_status_json_round_trips() -> None:
    fixture = load_exchange_status_fixture()

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/exchange/status").mock(
            return_value=Response(200, json=fixture)
        )
        result = runner.invoke(app, ["status", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    assert payload.get("exchange_active") == fixture.get("exchange_active")


def test_status_schedule_json_round_trips() -> None:
    fixture = load_exchange_schedule_fixture()

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/exchange/schedule").mock(
            return_value=Response(200, json=fixture)
        )
        result = runner.invoke(app, ["status", "schedule", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload.get("schedule") == fixture.get("schedule")


def test_status_announcements_json_round_trips() -> None:
    fixture = load_exchange_announcements_fixture()

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/exchange/announcements").mock(
            return_value=Response(200, json=fixture)
        )
        result = runner.invoke(app, ["status", "announcements", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload.get("announcements") == fixture.get("announcements")
