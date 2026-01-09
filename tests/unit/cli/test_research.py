from __future__ import annotations

import json
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


def test_research_topic_missing_exa_key_exits_with_error() -> None:
    exa_error = ValueError("EXA_API_KEY is required")
    with patch("kalshi_research.exa.ExaClient.from_env", side_effect=exa_error):
        result = runner.invoke(app, ["research", "topic", "Test topic"])

    assert result.exit_code == 1
    assert "EXA_API_KEY" in result.stdout


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
