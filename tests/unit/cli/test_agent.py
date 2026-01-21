"""Unit tests for `kalshi_research.cli.agent` helpers."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
import typer
from typer.testing import CliRunner

from kalshi_research.cli import agent as agent_module
from kalshi_research.cli import app as root_app
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

runner = CliRunner()


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


def test_agent_analyze_command_outputs_json_by_default() -> None:
    mock_execute = AsyncMock(return_value=({"analysis": {}}, False))

    with (
        patch("kalshi_research.cli.agent._execute_analysis", mock_execute),
        patch("kalshi_research.cli.agent.run_async", side_effect=lambda coro: asyncio.run(coro)),
        patch("kalshi_research.cli.agent._output_analysis_json") as mock_output,
        patch("kalshi_research.cli.agent._render_analysis_human") as mock_human,
    ):
        result = runner.invoke(root_app, ["agent", "analyze", "TEST"])

    assert result.exit_code == 0
    assert mock_output.call_count == 1
    assert mock_human.call_count == 0
    assert mock_output.call_args.args[2] is True  # quiet=True for JSON-only output


def test_agent_analyze_command_outputs_human_when_flag_set() -> None:
    mock_execute = AsyncMock(return_value=({"analysis": {}}, False))

    with (
        patch("kalshi_research.cli.agent._execute_analysis", mock_execute),
        patch("kalshi_research.cli.agent.run_async", side_effect=lambda coro: asyncio.run(coro)),
        patch("kalshi_research.cli.agent._output_analysis_json") as mock_output,
        patch("kalshi_research.cli.agent._render_analysis_human") as mock_human,
    ):
        result = runner.invoke(root_app, ["agent", "analyze", "TEST", "--human"])

    assert result.exit_code == 0
    assert mock_human.call_count == 1
    assert mock_output.call_count == 0


def test_agent_research_command_outputs_human_by_default() -> None:
    mock_execute = AsyncMock(return_value={"ticker": "TEST"})

    with (
        patch("kalshi_research.cli.agent._execute_research", mock_execute),
        patch("kalshi_research.cli.agent.run_async", side_effect=lambda coro: asyncio.run(coro)),
        patch("kalshi_research.cli.agent._write_json_output") as mock_json,
        patch("kalshi_research.cli.agent._render_research_summary") as mock_human,
    ):
        result = runner.invoke(root_app, ["agent", "research", "TEST"])

    assert result.exit_code == 0
    assert mock_human.call_count == 1
    assert mock_json.call_count == 0


def test_agent_research_command_outputs_json_when_flag_set() -> None:
    mock_execute = AsyncMock(return_value={"ticker": "TEST"})

    with (
        patch("kalshi_research.cli.agent._execute_research", mock_execute),
        patch("kalshi_research.cli.agent.run_async", side_effect=lambda coro: asyncio.run(coro)),
        patch("kalshi_research.cli.agent._write_json_output") as mock_json,
        patch("kalshi_research.cli.agent._render_research_summary") as mock_human,
    ):
        result = runner.invoke(root_app, ["agent", "research", "TEST", "--json"])

    assert result.exit_code == 0
    assert mock_json.call_count == 1
    assert mock_human.call_count == 0


@pytest.mark.asyncio
async def test_execute_analysis_adds_warning_for_mock_synthesizer_when_not_quiet() -> None:
    from kalshi_research.agent.schemas import (
        AgentRunResult,
        AnalysisFactor,
        AnalysisResult,
        VerificationReport,
    )
    from kalshi_research.exa.policy import ExaMode

    agent_run_result = AgentRunResult(
        analysis=AnalysisResult(
            ticker="TEST",
            market_prob=0.5,
            predicted_prob=55,
            confidence="medium",
            reasoning="Because reasons.",
            factors=[
                AnalysisFactor(
                    description="Factor A",
                    impact="up",
                    source_url="https://example.com",
                )
            ],
            sources=["https://example.com"],
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            model_id="mock-v1",
        ),
        verification=VerificationReport(passed=True),
        research=None,
        total_cost_usd=0.01,
    )

    class FakeKernel:
        def __init__(self, **_kwargs: object) -> None:
            pass

        async def analyze(self, *, ticker: str, research_mode: str) -> AgentRunResult:
            assert ticker == "TEST"
            assert research_mode == "fast"
            return agent_run_result

    mock_kalshi = AsyncMock()
    mock_kalshi.__aenter__.return_value = mock_kalshi
    mock_kalshi.__aexit__.return_value = None

    mock_exa = AsyncMock()
    mock_exa.__aenter__.return_value = mock_exa
    mock_exa.__aexit__.return_value = None

    @asynccontextmanager
    async def mock_public_client():
        yield mock_kalshi

    @asynccontextmanager
    async def mock_exa_from_env(*_args: object, **_kwargs: object):
        yield mock_exa

    from kalshi_research.agent.providers.llm import MockSynthesizer

    with (
        patch("kalshi_research.cli.client_factory.public_client", mock_public_client),
        patch("kalshi_research.exa.client.ExaClient.from_env", mock_exa_from_env),
        patch("kalshi_research.agent.orchestrator.AgentKernel", FakeKernel),
        patch(
            "kalshi_research.agent.providers.llm.get_synthesizer", return_value=MockSynthesizer()
        ),
        patch("kalshi_research.agent.ResearchAgent"),
        patch.object(agent_module.console, "print") as mock_print,
    ):
        result, is_mock = await agent_module._execute_analysis(
            "TEST",
            ExaMode.FAST,
            max_exa_usd=0.25,
            max_llm_usd=0.25,
            quiet=False,
        )

    assert is_mock is True
    assert "warning" in result
    printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "MockSynthesizer" in printed
