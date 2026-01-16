from __future__ import annotations

import json
import os
import runpy
import sys
from unittest.mock import patch

import pytest
import respx
from httpx import Response
from typer.testing import CliRunner

from kalshi_research.cli import app
from tests.golden_fixtures import load_golden_response

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "kalshi-research v0.1.0" in result.stdout


def test_global_env_uses_env_var_when_no_flag() -> None:
    from kalshi_research.api.config import Environment, get_config, set_environment

    set_environment(Environment.PRODUCTION)
    try:
        with patch.dict(os.environ, {"KALSHI_ENVIRONMENT": "demo"}, clear=False):
            result = runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert get_config().environment == Environment.DEMO
    finally:
        set_environment(Environment.PRODUCTION)


def test_global_env_flag_overrides_env_var() -> None:
    from kalshi_research.api.config import Environment, get_config, set_environment

    set_environment(Environment.PRODUCTION)
    try:
        with patch.dict(os.environ, {"KALSHI_ENVIRONMENT": "demo"}, clear=False):
            result = runner.invoke(app, ["--env", "prod", "version"])

        assert result.exit_code == 0
        assert get_config().environment == Environment.PRODUCTION
    finally:
        set_environment(Environment.PRODUCTION)


def test_invalid_global_env_exits_with_error() -> None:
    with patch.dict(os.environ, {"KALSHI_ENVIRONMENT": "nope"}, clear=False):
        result = runner.invoke(app, ["version"])

    assert result.exit_code == 1
    assert "Invalid environment" in result.stdout


def test_module_entrypoint_executes() -> None:
    with (
        patch.object(sys, "argv", ["kalshi"]),
        pytest.raises(SystemExit) as exc,
    ):
        runpy.run_module("kalshi_research.cli.__main__", run_name="__main__")
    assert exc.value.code == 2


@respx.mock
def test_status_command() -> None:
    response_json = load_golden_response("exchange_status_response.json")
    route = respx.get("https://api.elections.kalshi.com/trade-api/v2/exchange/status").mock(
        return_value=Response(200, json=response_json)
    )

    result = runner.invoke(app, ["status"])

    assert route.called
    assert result.exit_code == 0
    assert "Exchange Status" in result.stdout
    assert "exchange_active" in result.stdout
    assert "trading_active" in result.stdout


@respx.mock
def test_status_command_json_output() -> None:
    response_json = load_golden_response("exchange_status_response.json")
    route = respx.get("https://api.elections.kalshi.com/trade-api/v2/exchange/status").mock(
        return_value=Response(200, json=response_json)
    )

    result = runner.invoke(app, ["status", "--json"])

    assert route.called
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload == response_json


@respx.mock
def test_status_command_unexpected_type_exits_with_error() -> None:
    route = respx.get("https://api.elections.kalshi.com/trade-api/v2/exchange/status").mock(
        return_value=Response(200, json=["not-a-dict"])
    )

    result = runner.invoke(app, ["status"])

    assert route.called
    assert result.exit_code == 1
    assert "Unexpected exchange status response type" in result.stdout


@respx.mock
def test_status_command_api_error_exits_cleanly() -> None:
    route = respx.get("https://api.elections.kalshi.com/trade-api/v2/exchange/status").mock(
        return_value=Response(500, text="Boom")
    )

    result = runner.invoke(app, ["status"])

    assert route.called
    assert result.exit_code == 1
    assert "API Error 500" in result.stdout


@respx.mock
def test_status_command_generic_error_exits_cleanly() -> None:
    route = respx.get("https://api.elections.kalshi.com/trade-api/v2/exchange/status").mock(
        side_effect=RuntimeError("Boom")
    )

    result = runner.invoke(app, ["status"])

    assert route.called
    assert result.exit_code == 1
    assert "Error:" in result.stdout
    assert "Boom" in result.stdout
