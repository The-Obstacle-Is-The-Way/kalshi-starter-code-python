"""Unit tests for `kalshi_research.cli.agent` helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import typer

from kalshi_research.cli import agent as agent_module
from kalshi_research.cli.agent import (
    _output_analysis_json,
    _parse_exa_mode,
    _render_analysis_human,
    _render_factors_table,
    _render_research_summary,
    _write_json_output,
)
from kalshi_research.exa.policy import ExaMode

if TYPE_CHECKING:
    from pathlib import Path


def test_parse_exa_mode_is_case_insensitive() -> None:
    assert _parse_exa_mode("FAST") is ExaMode.FAST
    assert _parse_exa_mode("standard") is ExaMode.STANDARD


def test_parse_exa_mode_invalid_exits_1() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        _parse_exa_mode("nope")
    assert exc_info.value.exit_code == 1


def test_write_json_output_writes_stdout_when_no_file() -> None:
    with patch("kalshi_research.cli.agent.typer.echo") as mock_echo:
        _write_json_output({"a": 1}, output_file=None)

    assert mock_echo.call_count == 1
    payload = json.loads(mock_echo.call_args.args[0])
    assert payload == {"a": 1}


def test_write_json_output_writes_file_when_path_given(tmp_path: Path) -> None:
    out_path = tmp_path / "out.json"
    _write_json_output({"a": 1}, output_file=str(out_path))

    assert out_path.exists()
    assert json.loads(out_path.read_text(encoding="utf-8")) == {"a": 1}


def test_render_factors_table_empty_prints_message() -> None:
    with patch.object(agent_module.console, "print") as mock_print:
        _render_factors_table([])

    printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "No factors found" in printed


def test_render_research_summary_writes_file(tmp_path: Path) -> None:
    out_path = tmp_path / "summary.json"
    result: dict[str, object] = {
        "ticker": "TEST",
        "title": "Test Market",
        "mode": "fast",
        "total_cost_usd": 0.01,
        "budget_usd": 0.05,
        "budget_exhausted": False,
        "factors": [
            {
                "factor_text": "Example factor",
                "source_url": "https://example.com",
                "confidence": "medium",
            }
        ],
    }

    with patch.object(agent_module.console, "print"):
        _render_research_summary(result, output_file=str(out_path))

    assert out_path.exists()
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["ticker"] == "TEST"


def test_output_analysis_json_writes_file_and_prints_when_not_quiet(tmp_path: Path) -> None:
    out_path = tmp_path / "analysis.json"
    result: dict[str, object] = {"analysis": {"ticker": "TEST"}}

    with patch.object(agent_module.console, "print") as mock_print:
        _output_analysis_json(result, output_file=str(out_path), quiet=False)

    assert out_path.exists()
    assert json.loads(out_path.read_text(encoding="utf-8"))["analysis"]["ticker"] == "TEST"
    assert any("Results written to" in str(call.args[0]) for call in mock_print.call_args_list)


def test_render_analysis_human_renders_sections() -> None:
    from rich.panel import Panel

    result: dict[str, object] = {
        "analysis": {
            "ticker": "TEST",
            "predicted_prob": 55,
            "market_prob": 0.5,
            "confidence": "medium",
            "reasoning": "Because reasons.",
            "factors": [{"description": "Factor A", "impact": "positive"}],
        },
        "verification": {"passed": False, "issues": ["Issue 1"]},
        "research": {"total_cost_usd": 0.01},
        "total_cost_usd": 0.02,
    }

    with patch.object(agent_module.console, "print") as mock_print:
        _render_analysis_human(result)

    printed_args = [call.args[0] for call in mock_print.call_args_list if call.args]

    assert any(isinstance(arg, Panel) and arg.title == "Analysis Result" for arg in printed_args)
    assert any(isinstance(arg, str) and "Reasoning" in arg for arg in printed_args)
    assert any(isinstance(arg, str) and "Verification Issues" in arg for arg in printed_args)
