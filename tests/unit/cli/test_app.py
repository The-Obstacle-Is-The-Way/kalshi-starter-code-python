from __future__ import annotations

import os
from unittest.mock import patch

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
