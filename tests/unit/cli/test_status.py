from __future__ import annotations

import json

import pytest
import respx
import typer
from httpx import Response
from typer.testing import CliRunner

from kalshi_research.cli import app
from kalshi_research.cli.status import _render_exchange_schedule, _render_standard_hours
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


def test_status_outputs_table() -> None:
    fixture = load_exchange_status_fixture()

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/exchange/status").mock(
            return_value=Response(200, json=fixture)
        )
        result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "Exchange Status" in result.stdout
    assert "exchange_active" in result.stdout


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


def test_status_schedule_outputs_tables() -> None:
    fixture = load_exchange_schedule_fixture()
    schedule = fixture.get("schedule")
    assert isinstance(schedule, dict)
    schedule["maintenance_windows"] = [
        {
            "start_datetime": "2026-01-01T00:00:00Z",
            "end_datetime": "2026-01-01T01:00:00Z",
        }
    ]

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/exchange/schedule").mock(
            return_value=Response(200, json=fixture)
        )
        result = runner.invoke(app, ["status", "schedule"])

    assert result.exit_code == 0
    assert "Standard Hours" in result.stdout
    assert "monday" in result.stdout.lower()
    assert "Maintenance Windows" in result.stdout


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


def test_status_announcements_outputs_table() -> None:
    fixture = load_exchange_announcements_fixture()
    fixture["announcements"] = [
        {
            "type": "maintenance",
            "message": "Scheduled maintenance window",
            "delivery_time": "2026-01-01T00:00:00Z",
            "status": "active",
        }
    ]

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/exchange/announcements").mock(
            return_value=Response(200, json=fixture)
        )
        result = runner.invoke(app, ["status", "announcements"])

    assert result.exit_code == 0
    assert "Exchange Announcements" in result.stdout


def test_status_announcements_empty_reports_message() -> None:
    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/exchange/announcements").mock(
            return_value=Response(200, json={"announcements": []})
        )
        result = runner.invoke(app, ["status", "announcements"])

    assert result.exit_code == 0
    assert "No announcements returned" in result.stdout


def test_status_api_error_exits_1() -> None:
    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/exchange/status").mock(
            return_value=Response(500, json={"error": "boom"})
        )
        result = runner.invoke(app, ["status"])

    assert result.exit_code == 1
    assert "API Error 500" in result.stdout


def test_status_schedule_api_error_exits_1() -> None:
    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/exchange/schedule").mock(
            return_value=Response(500, json={"error": "boom"})
        )
        result = runner.invoke(app, ["status", "schedule"])

    assert result.exit_code == 1
    assert "API Error 500" in result.stdout


def test_status_announcements_api_error_exits_1() -> None:
    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/exchange/announcements").mock(
            return_value=Response(500, json={"error": "boom"})
        )
        result = runner.invoke(app, ["status", "announcements"])

    assert result.exit_code == 1
    assert "API Error 500" in result.stdout


def test_render_exchange_schedule_rejects_unexpected_shape() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        _render_exchange_schedule({"schedule": "not-a-dict"})

    assert exc_info.value.exit_code == 1


def test_render_standard_hours_handles_empty_input() -> None:
    _render_standard_hours([])
