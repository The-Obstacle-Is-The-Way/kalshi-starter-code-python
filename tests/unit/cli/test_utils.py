"""Tests for kalshi_research.cli.utils module."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
import typer

from kalshi_research.api.exceptions import KalshiAPIError
from kalshi_research.cli.utils import exit_kalshi_api_error, run_async


class TestRunAsync:
    """Tests for run_async helper."""

    def test_returns_coroutine_result(self) -> None:
        """run_async should return the result of the coroutine."""

        async def coro() -> str:
            return "hello"

        result = run_async(coro())
        assert result == "hello"

    def test_propagates_exceptions(self) -> None:
        """run_async should propagate exceptions from the coroutine."""

        async def failing_coro() -> None:
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            run_async(failing_coro())

    def test_handles_keyboard_interrupt(self) -> None:
        """run_async should handle KeyboardInterrupt and exit with code 130."""

        async def interrupted_coro() -> None:
            raise KeyboardInterrupt

        with pytest.raises(typer.Exit) as exc_info:
            run_async(interrupted_coro())

        assert exc_info.value.exit_code == 130

    def test_prints_interrupted_message_on_ctrl_c(self) -> None:
        """run_async should print 'Interrupted' on KeyboardInterrupt."""

        async def interrupted_coro() -> None:
            raise KeyboardInterrupt

        with (
            patch("kalshi_research.cli.utils.console.print") as mock_print,
            pytest.raises(typer.Exit),
        ):
            run_async(interrupted_coro())

        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "Interrupted" in call_args

    def test_async_operations_work(self) -> None:
        """run_async should properly execute async operations."""

        async def async_op() -> int:
            await asyncio.sleep(0.001)  # Tiny sleep to verify async works
            return 42

        result = run_async(async_op())
        assert result == 42


class TestExitKalshiApiError:
    """Tests for exit_kalshi_api_error helper."""

    def test_exits_with_code_1_for_non_404_error(self) -> None:
        """exit_kalshi_api_error should exit with code 1 for non-404 errors."""
        error = KalshiAPIError(500, "Internal Server Error")

        with pytest.raises(typer.Exit) as exc_info:
            exit_kalshi_api_error(error)

        assert exc_info.value.exit_code == 1

    def test_exits_with_code_2_for_404_error(self) -> None:
        """exit_kalshi_api_error should exit with code 2 for 404 (not found)."""
        error = KalshiAPIError(404, "Market not found")

        with pytest.raises(typer.Exit) as exc_info:
            exit_kalshi_api_error(error)

        assert exc_info.value.exit_code == 2

    def test_prints_error_message_without_context(self) -> None:
        """exit_kalshi_api_error should print status code and message."""
        error = KalshiAPIError(400, "Bad Request")

        with (
            patch("kalshi_research.cli.utils.console.print") as mock_print,
            pytest.raises(typer.Exit),
        ):
            exit_kalshi_api_error(error)

        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "400" in call_args
        assert "Bad Request" in call_args

    def test_prints_error_message_with_context(self) -> None:
        """exit_kalshi_api_error should include context in the message."""
        error = KalshiAPIError(404, "Market not found")

        with (
            patch("kalshi_research.cli.utils.console.print") as mock_print,
            pytest.raises(typer.Exit),
        ):
            exit_kalshi_api_error(error, context="fetching market data")

        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "404" in call_args
        assert "Market not found" in call_args
        assert "while fetching market data" in call_args

    def test_exits_with_code_1_for_401_unauthorized(self) -> None:
        """exit_kalshi_api_error should exit with code 1 for 401 (unauthorized)."""
        error = KalshiAPIError(401, "Unauthorized")

        with pytest.raises(typer.Exit) as exc_info:
            exit_kalshi_api_error(error)

        assert exc_info.value.exit_code == 1

    def test_exits_with_code_1_for_429_rate_limit(self) -> None:
        """exit_kalshi_api_error should exit with code 1 for 429 (rate limit)."""
        error = KalshiAPIError(429, "Rate limit exceeded")

        with pytest.raises(typer.Exit) as exc_info:
            exit_kalshi_api_error(error)

        assert exc_info.value.exit_code == 1
