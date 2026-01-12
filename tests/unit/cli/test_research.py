from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

from typer.testing import CliRunner

from kalshi_research.cli import app

runner = CliRunner()


def test_research_context_help() -> None:
    result = runner.invoke(app, ["research", "context", "--help"])
    assert result.exit_code == 0
    assert "Market ticker to research" in result.stdout


def test_research_topic_help() -> None:
    result = runner.invoke(app, ["research", "topic", "--help"])
    assert result.exit_code == 0
    assert "Topic or question to research" in result.stdout


def test_research_context_missing_exa_key_exits_with_error(make_market) -> None:
    from kalshi_research.api.models.market import Market

    market = Market.model_validate(make_market(ticker="TEST-MARKET"))
    exa_error = ValueError("EXA_API_KEY is required")

    mock_kalshi = AsyncMock()
    mock_kalshi.__aenter__.return_value = mock_kalshi
    mock_kalshi.__aexit__.return_value = AsyncMock()
    mock_kalshi.get_market = AsyncMock(return_value=market)

    with (
        patch("kalshi_research.api.KalshiPublicClient", return_value=mock_kalshi),
        patch("kalshi_research.exa.ExaClient.from_env", side_effect=exa_error),
    ):
        result = runner.invoke(app, ["research", "context", "TEST-MARKET"])

    assert result.exit_code == 1
    assert "EXA_API_KEY" in result.stdout
    assert "Set EXA_API_KEY" in result.stdout


def test_research_topic_missing_exa_key_exits_with_error() -> None:
    exa_error = ValueError("EXA_API_KEY is required")
    with patch("kalshi_research.exa.ExaClient.from_env", side_effect=exa_error):
        result = runner.invoke(app, ["research", "topic", "Test topic"])

    assert result.exit_code == 1
    assert "EXA_API_KEY" in result.stdout
    assert "Set EXA_API_KEY" in result.stdout


def test_research_similar_missing_exa_key_exits_with_error() -> None:
    exa_error = ValueError("EXA_API_KEY is required")
    with patch("kalshi_research.exa.ExaClient.from_env", side_effect=exa_error):
        result = runner.invoke(app, ["research", "similar", "https://example.com"])

    assert result.exit_code == 1
    assert "EXA_API_KEY" in result.stdout
    assert "Set EXA_API_KEY" in result.stdout


def test_research_deep_missing_exa_key_exits_with_error() -> None:
    exa_error = ValueError("EXA_API_KEY is required")
    with patch("kalshi_research.exa.ExaClient.from_env", side_effect=exa_error):
        result = runner.invoke(app, ["research", "deep", "Test topic"])

    assert result.exit_code == 1
    assert "EXA_API_KEY" in result.stdout
    assert "Set EXA_API_KEY" in result.stdout


def test_research_similar_json_output() -> None:
    from kalshi_research.exa.models.search import SearchResult
    from kalshi_research.exa.models.similar import FindSimilarResponse

    response = FindSimilarResponse(
        request_id="req-1",
        results=[
            SearchResult(
                id="1",
                url="https://example.com/a",
                title="Example A",
                score=0.9,
            )
        ],
    )

    mock_exa = AsyncMock()
    mock_exa.__aenter__.return_value = mock_exa
    mock_exa.__aexit__.return_value = AsyncMock()
    mock_exa.find_similar = AsyncMock(return_value=response)

    with patch("kalshi_research.exa.ExaClient.from_env", return_value=mock_exa):
        result = runner.invoke(app, ["research", "similar", "https://example.com", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["requestId"] == "req-1"
    assert payload["results"][0]["title"] == "Example A"


def test_research_similar_table_output_includes_cost() -> None:
    from kalshi_research.exa.models.common import CostDollars
    from kalshi_research.exa.models.search import SearchResult
    from kalshi_research.exa.models.similar import FindSimilarResponse

    response = FindSimilarResponse(
        request_id="req-1",
        results=[
            SearchResult(
                id="1",
                url="https://example.com/a",
                title="Example A",
                score=0.9,
            )
        ],
        cost_dollars=CostDollars(total=0.005),
    )

    mock_exa = AsyncMock()
    mock_exa.__aenter__.return_value = mock_exa
    mock_exa.__aexit__.return_value = AsyncMock()
    mock_exa.find_similar = AsyncMock(return_value=response)

    with patch("kalshi_research.exa.ExaClient.from_env", return_value=mock_exa):
        result = runner.invoke(
            app, ["research", "similar", "https://example.com", "--num-results", "1"]
        )

    assert result.exit_code == 0
    assert "Exa Similar Pages" in result.stdout
    assert "Example A" in result.stdout
    assert "Cost:" in result.stdout


def test_research_deep_wait_json_output() -> None:
    from kalshi_research.exa.models.research import ResearchOutput, ResearchStatus, ResearchTask

    created = ResearchTask(
        research_id="research-1",
        status=ResearchStatus.PENDING,
        created_at=1700000000,
        model="exa-research",
        instructions="Test",
    )
    completed = ResearchTask(
        research_id="research-1",
        status=ResearchStatus.COMPLETED,
        created_at=1700000000,
        model="exa-research",
        instructions="Test",
        output=ResearchOutput(content="Done", parsed=None),
    )

    mock_exa = AsyncMock()
    mock_exa.__aenter__.return_value = mock_exa
    mock_exa.__aexit__.return_value = AsyncMock()
    mock_exa.create_research_task = AsyncMock(return_value=created)
    mock_exa.wait_for_research = AsyncMock(return_value=completed)

    with patch("kalshi_research.exa.ExaClient.from_env", return_value=mock_exa):
        result = runner.invoke(app, ["research", "deep", "Test topic", "--wait", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["researchId"] == "research-1"
    assert payload["status"] == "completed"
    assert payload["output"]["content"] == "Done"


def test_research_deep_schema_invalid_json_exits_with_error(tmp_path: Path) -> None:
    schema_file = tmp_path / "schema.json"
    schema_file.write_text("{not json", encoding="utf-8")

    result = runner.invoke(app, ["research", "deep", "Test topic", "--schema", str(schema_file)])

    assert result.exit_code == 1
    assert "Schema file is not valid JSON" in result.stdout


def test_research_deep_schema_root_not_object_exits_with_error(tmp_path: Path) -> None:
    schema_file = tmp_path / "schema.json"
    schema_file.write_text("[]", encoding="utf-8")

    result = runner.invoke(app, ["research", "deep", "Test topic", "--schema", str(schema_file)])

    assert result.exit_code == 1
    assert "Schema JSON must be an object" in result.stdout


def test_research_deep_wait_timeout_exits_with_error() -> None:
    from kalshi_research.exa.models.research import ResearchStatus, ResearchTask

    created = ResearchTask(
        research_id="research-1",
        status=ResearchStatus.PENDING,
        created_at=1700000000,
        model="exa-research",
        instructions="Test",
    )

    mock_exa = AsyncMock()
    mock_exa.__aenter__.return_value = mock_exa
    mock_exa.__aexit__.return_value = AsyncMock()
    mock_exa.create_research_task = AsyncMock(return_value=created)
    mock_exa.wait_for_research = AsyncMock(side_effect=TimeoutError("Timed out"))

    with patch("kalshi_research.exa.ExaClient.from_env", return_value=mock_exa):
        result = runner.invoke(
            app, ["research", "deep", "Test topic", "--wait", "--timeout", "0.01"]
        )

    assert result.exit_code == 1
    assert "Timed out" in result.stdout


def test_research_deep_table_output_renders_task_data() -> None:
    from kalshi_research.exa.models.research import (
        ResearchCostDollars,
        ResearchOutput,
        ResearchStatus,
        ResearchTask,
    )

    task = ResearchTask(
        research_id="research-1",
        status=ResearchStatus.COMPLETED,
        created_at=1700000000,
        model="exa-research",
        instructions="Test",
        output=ResearchOutput(content="Done", parsed=None),
        cost_dollars=ResearchCostDollars(
            total=0.1, num_searches=1, num_pages=1, reasoning_tokens=1
        ),
    )

    mock_exa = AsyncMock()
    mock_exa.__aenter__.return_value = mock_exa
    mock_exa.__aexit__.return_value = AsyncMock()
    mock_exa.create_research_task = AsyncMock(return_value=task)

    with patch("kalshi_research.exa.ExaClient.from_env", return_value=mock_exa):
        result = runner.invoke(app, ["research", "deep", "Test topic"])

    assert result.exit_code == 0
    assert "Exa Research Task" in result.stdout
    assert "research-1" in result.stdout
    assert "Output" in result.stdout
    assert "Done" in result.stdout
    assert "Cost:" in result.stdout


def test_thesis_list_invalid_json_exits_with_error(tmp_path: Path) -> None:
    thesis_file = tmp_path / "theses.json"
    thesis_file.write_text("{not json", encoding="utf-8")

    with patch("kalshi_research.cli.research._get_thesis_file", return_value=thesis_file):
        result = runner.invoke(app, ["research", "thesis", "list"])

    assert result.exit_code == 1
    assert "Theses file is not valid JSON" in result.stdout


def test_research_thesis_create() -> None:
    with runner.isolated_filesystem():
        thesis_file = Path("theses.json")
        with patch("kalshi_research.cli.research._get_thesis_file", return_value=thesis_file):
            result = runner.invoke(
                app,
                [
                    "research",
                    "thesis",
                    "create",
                    "Test thesis",
                    "--markets",
                    "TICK1,TICK2",
                    "--your-prob",
                    "0.7",
                    "--market-prob",
                    "0.5",
                    "--confidence",
                    "0.8",
                ],
            )

        assert result.exit_code == 0
        assert "Thesis created" in result.stdout
        stored = json.loads(thesis_file.read_text(encoding="utf-8"))
        assert len(stored["theses"]) == 1


def test_research_thesis_create_with_research_accepts_suggestions() -> None:
    from kalshi_research.research.thesis import ThesisEvidence
    from kalshi_research.research.thesis_research import ResearchedThesisData

    now = datetime.now(UTC)
    research_data = ResearchedThesisData(
        suggested_bull_case="Better bull",
        suggested_bear_case="Better bear",
        bull_evidence=[
            ThesisEvidence(
                url="https://example.com/bull",
                title="Bull source",
                source_domain="example.com",
                published_date=now,
                snippet="Bull snippet",
                supports="bull",
                relevance_score=0.9,
                added_at=now,
            )
        ],
        bear_evidence=[],
        neutral_evidence=[],
        summary="Research summary",
        exa_cost_dollars=0.0123,
    )

    with runner.isolated_filesystem():
        thesis_file = Path("theses.json")
        with (
            patch("kalshi_research.cli.research._get_thesis_file", return_value=thesis_file),
            patch(
                "kalshi_research.cli.research._gather_thesis_research_data",
                new=AsyncMock(return_value=research_data),
            ),
        ):
            result = runner.invoke(
                app,
                [
                    "research",
                    "thesis",
                    "create",
                    "Test thesis",
                    "--markets",
                    "MKT1",
                    "--your-prob",
                    "0.7",
                    "--market-prob",
                    "0.5",
                    "--confidence",
                    "0.8",
                    "--with-research",
                    "--yes",
                ],
            )

        assert result.exit_code == 0
        assert "Research cost:" in result.stdout
        stored = json.loads(thesis_file.read_text(encoding="utf-8"))
        assert stored["theses"][0]["bull_case"] == "Better bull"
        assert stored["theses"][0]["bear_case"] == "Better bear"
        assert stored["theses"][0]["evidence"]
        assert stored["theses"][0]["research_summary"] == "Research summary"
        assert stored["theses"][0]["last_research_at"] is not None


def test_research_thesis_list_empty() -> None:
    with runner.isolated_filesystem():
        thesis_file = Path("theses.json")
        with patch("kalshi_research.cli.research._get_thesis_file", return_value=thesis_file):
            result = runner.invoke(app, ["research", "thesis", "list"])

    assert result.exit_code == 0
    assert "No theses" in result.stdout


def test_research_thesis_list_with_theses() -> None:
    with runner.isolated_filesystem():
        thesis_file = Path("theses.json")
        thesis_file.write_text(
            json.dumps(
                {
                    "theses": [
                        {
                            "id": "thesis-12345678",
                            "title": "Test Thesis",
                            "status": "active",
                            "your_probability": 0.7,
                            "market_probability": 0.5,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        with patch("kalshi_research.cli.research._get_thesis_file", return_value=thesis_file):
            result = runner.invoke(app, ["research", "thesis", "list"])

    assert result.exit_code == 0
    assert "thesis-" in result.stdout.lower() or "Test Thesis" in result.stdout


def test_research_thesis_show() -> None:
    with runner.isolated_filesystem():
        thesis_file = Path("theses.json")
        thesis_file.write_text(
            json.dumps(
                {
                    "theses": [
                        {
                            "id": "thesis-12345678",
                            "title": "Test Thesis",
                            "status": "active",
                            "your_probability": 0.7,
                            "market_probability": 0.5,
                            "confidence": 0.8,
                            "bull_case": "Bull case",
                            "bear_case": "Bear case",
                            "key_assumptions": ["Assumption 1"],
                            "invalidation_criteria": ["Criterion 1"],
                            "market_tickers": ["TICK1"],
                            "updates": [],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        with patch("kalshi_research.cli.research._get_thesis_file", return_value=thesis_file):
            result = runner.invoke(app, ["research", "thesis", "show", "thesis-1"])

    assert result.exit_code == 0
    assert "Test Thesis" in result.stdout


def test_research_thesis_resolve() -> None:
    with runner.isolated_filesystem():
        thesis_file = Path("theses.json")
        thesis_file.write_text(
            json.dumps(
                {
                    "theses": [
                        {
                            "id": "thesis-12345678",
                            "title": "Test Thesis",
                            "status": "active",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        with patch("kalshi_research.cli.research._get_thesis_file", return_value=thesis_file):
            result = runner.invoke(
                app, ["research", "thesis", "resolve", "thesis-1", "--outcome", "yes"]
            )

    assert result.exit_code == 0
    assert "resolved" in result.stdout.lower()


def test_research_thesis_check_invalidation_no_signals(tmp_path: Path) -> None:
    from kalshi_research.research.invalidation import InvalidationReport

    thesis_id = "thesis-12345678"
    thesis_file = tmp_path / "theses.json"
    thesis_file.write_text(
        json.dumps(
            {
                "theses": [
                    {
                        "id": thesis_id,
                        "title": "Test Thesis",
                        "market_tickers": ["MKT1"],
                        "your_probability": 0.7,
                        "market_probability": 0.5,
                        "confidence": 0.8,
                        "bull_case": "Bull",
                        "bear_case": "Bear",
                        "key_assumptions": [],
                        "invalidation_criteria": [],
                        "status": "active",
                        "created_at": datetime.now(UTC).isoformat(),
                        "resolved_at": None,
                        "actual_outcome": None,
                        "updates": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    mock_exa = AsyncMock()
    mock_exa.__aenter__.return_value = mock_exa
    mock_exa.__aexit__.return_value = None

    report = InvalidationReport(
        thesis_id=thesis_id,
        thesis_title="Test Thesis",
        checked_at=datetime.now(UTC),
        signals=[],
        recommendation="Hold.",
    )

    detector_instance = AsyncMock()
    detector_instance.check_thesis = AsyncMock(return_value=report)

    with (
        patch("kalshi_research.cli.research._get_thesis_file", return_value=thesis_file),
        patch("kalshi_research.exa.ExaClient.from_env", return_value=mock_exa),
        patch(
            "kalshi_research.research.invalidation.InvalidationDetector",
            return_value=detector_instance,
        ),
    ):
        result = runner.invoke(app, ["research", "thesis", "check-invalidation", "thesis-1"])

    assert result.exit_code == 0
    assert "No invalidation signals found" in result.stdout


def test_research_thesis_check_invalidation_with_signals(tmp_path: Path) -> None:
    from kalshi_research.research.invalidation import (
        InvalidationReport,
        InvalidationSeverity,
        InvalidationSignal,
    )

    thesis_id = "thesis-12345678"
    thesis_file = tmp_path / "theses.json"
    thesis_file.write_text(
        json.dumps(
            {
                "theses": [
                    {
                        "id": thesis_id,
                        "title": "Test Thesis",
                        "market_tickers": ["MKT1"],
                        "your_probability": 0.7,
                        "market_probability": 0.5,
                        "confidence": 0.8,
                        "bull_case": "Bull",
                        "bear_case": "Bear",
                        "key_assumptions": [],
                        "invalidation_criteria": [],
                        "status": "active",
                        "created_at": datetime.now(UTC).isoformat(),
                        "resolved_at": None,
                        "actual_outcome": None,
                        "updates": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    mock_exa = AsyncMock()
    mock_exa.__aenter__.return_value = mock_exa
    mock_exa.__aexit__.return_value = None

    report = InvalidationReport(
        thesis_id=thesis_id,
        thesis_title="Test Thesis",
        checked_at=datetime.now(UTC),
        signals=[
            InvalidationSignal(
                severity=InvalidationSeverity.HIGH,
                title="Bad news",
                url="https://example.com/bad",
                source_domain="example.com",
                published_at=datetime.now(UTC),
                reason="Contradicts thesis",
                snippet="Snippet",
            )
        ],
        recommendation="Re-evaluate.",
    )

    detector_instance = AsyncMock()
    detector_instance.check_thesis = AsyncMock(return_value=report)

    with (
        patch("kalshi_research.cli.research._get_thesis_file", return_value=thesis_file),
        patch("kalshi_research.exa.ExaClient.from_env", return_value=mock_exa),
        patch(
            "kalshi_research.research.invalidation.InvalidationDetector",
            return_value=detector_instance,
        ),
    ):
        result = runner.invoke(app, ["research", "thesis", "check-invalidation", "thesis-1"])

    assert result.exit_code == 0
    assert "Potential Invalidation Signals" in result.stdout
    assert "Bad news" in result.stdout


def test_research_thesis_suggest_prints_suggestions() -> None:
    from kalshi_research.research.thesis_research import ThesisSuggestion

    mock_exa = AsyncMock()
    mock_exa.__aenter__.return_value = mock_exa
    mock_exa.__aexit__.return_value = None

    suggester_instance = AsyncMock()
    suggester_instance.suggest_theses = AsyncMock(
        return_value=[
            ThesisSuggestion(
                source_title="Source",
                source_url="https://example.com",
                key_insight="Insight",
                suggested_thesis="Suggested thesis",
                confidence="medium",
            )
        ]
    )

    with (
        patch("kalshi_research.exa.ExaClient.from_env", return_value=mock_exa),
        patch(
            "kalshi_research.research.thesis_research.ThesisSuggester",
            return_value=suggester_instance,
        ),
    ):
        result = runner.invoke(app, ["research", "thesis", "suggest"])

    assert result.exit_code == 0
    assert "Thesis Suggestions" in result.stdout
    assert "Suggested thesis" in result.stdout


@patch("kalshi_research.data.DatabaseManager")
def test_research_backtest(mock_db_cls: MagicMock) -> None:
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = AsyncMock()
    mock_db_cls.return_value = mock_db

    with runner.isolated_filesystem():
        db_path = Path("data/kalshi.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.touch()

        thesis_file = Path("data/theses.json")
        thesis_file.parent.mkdir(parents=True, exist_ok=True)
        thesis_file.write_text(json.dumps({"theses": []}), encoding="utf-8")

        result = runner.invoke(
            app,
            [
                "research",
                "backtest",
                "--start",
                "2024-01-01",
                "--end",
                "2024-12-31",
            ],
        )

    assert result.exit_code == 0
    assert "No resolved theses to backtest" in result.stdout


def test_parse_backtest_dates_includes_end_date() -> None:
    from kalshi_research.cli.research import _parse_backtest_dates

    start_dt, end_dt_exclusive = _parse_backtest_dates("2024-06-30", "2024-06-30")

    assert start_dt == datetime(2024, 6, 30, 0, 0, tzinfo=UTC)
    assert end_dt_exclusive == datetime(2024, 7, 1, 0, 0, tzinfo=UTC)


@patch("kalshi_research.data.DatabaseManager")
def test_research_thesis_show_with_positions(mock_db_cls: MagicMock) -> None:
    mock_position = MagicMock()
    mock_position.ticker = "TEST-TICKER"
    mock_position.side = "yes"
    mock_position.quantity = 100
    mock_position.avg_price_cents = 55
    mock_position.unrealized_pnl_cents = 500

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_position]

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    thesis_data = {
        "theses": [
            {
                "id": "thesis-12345678",
                "title": "Test Thesis",
                "status": "active",
                "your_probability": 0.7,
                "market_probability": 0.5,
                "confidence": 0.8,
                "bull_case": "Bull case",
                "bear_case": "Bear case",
                "key_assumptions": ["Assumption 1"],
                "invalidation_criteria": ["Criterion 1"],
                "market_tickers": ["TEST-TICKER"],
                "updates": [],
            }
        ]
    }
    mock_file = mock_open(read_data=json.dumps(thesis_data))

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.open", mock_file),
    ):
        result = runner.invoke(app, ["research", "thesis", "show", "thesis-1", "--with-positions"])

    assert result.exit_code == 0
    assert "Test Thesis" in result.stdout
    assert "position" in result.stdout.lower() or "TEST-TICKER" in result.stdout


def test_research_thesis_list_full_flag_disables_truncation() -> None:
    title_suffix = "TAILTITLE"
    long_title = f"{'A' * 55}{title_suffix}"
    id_suffix = "TAILID"
    thesis_id = f"12345678-{'X' * 10}{id_suffix}"

    theses = {
        "theses": [
            {
                "id": thesis_id,
                "title": long_title,
                "your_probability": 0.7,
                "market_probability": 0.5,
                "status": "active",
            }
        ]
    }

    with patch("kalshi_research.cli.research._load_theses", return_value=theses):
        result_default = runner.invoke(app, ["research", "thesis", "list"])

    assert result_default.exit_code == 0
    assert title_suffix not in result_default.stdout
    assert id_suffix not in result_default.stdout

    with patch("kalshi_research.cli.research._load_theses", return_value=theses):
        result_full = runner.invoke(app, ["research", "thesis", "list", "--full"])

    assert result_full.exit_code == 0
    assert title_suffix in result_full.stdout
    assert id_suffix in result_full.stdout
