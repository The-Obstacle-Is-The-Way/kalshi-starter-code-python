from __future__ import annotations

import json
import os
import runpy
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from kalshi_research.cli import app

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


@patch("kalshi_research.api.KalshiPublicClient")
def test_status_command(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get_exchange_status = AsyncMock(
        return_value={"exchange_active": True, "trading_active": True, "maintenance": False}
    )
    mock_client_cls.return_value = mock_client

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "Exchange Status" in result.stdout
    assert "exchange_active" in result.stdout
    assert "maintenance" in result.stdout


@patch("kalshi_research.api.KalshiPublicClient")
def test_status_command_json_output(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get_exchange_status = AsyncMock(return_value={"exchange_active": True})
    mock_client_cls.return_value = mock_client

    result = runner.invoke(app, ["status", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["exchange_active"] is True


@patch("kalshi_research.api.KalshiPublicClient")
def test_status_command_unexpected_type_exits_with_error(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get_exchange_status = AsyncMock(return_value=["not-a-dict"])
    mock_client_cls.return_value = mock_client

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 1
    assert "Unexpected exchange status response type" in result.stdout


@patch("kalshi_research.api.KalshiPublicClient")
def test_status_command_api_error_exits_cleanly(mock_client_cls: MagicMock) -> None:
    from kalshi_research.api.exceptions import KalshiAPIError

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get_exchange_status = AsyncMock(side_effect=KalshiAPIError(500, "Boom"))
    mock_client_cls.return_value = mock_client

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 1
    assert "API Error 500" in result.stdout


@patch("kalshi_research.api.KalshiPublicClient")
def test_status_command_generic_error_exits_cleanly(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get_exchange_status = AsyncMock(side_effect=RuntimeError("Boom"))
    mock_client_cls.return_value = mock_client

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 1
    assert "Error:" in result.stdout
    assert "Boom" in result.stdout
