"""Tests for kalshi_research.cli.utils module."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
import typer

from kalshi_research.cli.utils import run_async


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
