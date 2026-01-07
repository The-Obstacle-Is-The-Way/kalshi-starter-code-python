"""Extended CLI tests for alerts, analysis, and research commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from kalshi_research.cli import app

runner = CliRunner()


# ==================== Alerts CLI Tests ====================


@patch("kalshi_research.alerts.AlertMonitor")
def test_alerts_list_empty(mock_monitor_cls: MagicMock) -> None:
    """Test listing alerts when none exist."""
    mock_monitor = MagicMock()
    mock_monitor.list_conditions.return_value = []
    mock_monitor_cls.return_value = mock_monitor

    with patch("pathlib.Path.exists", return_value=False):
        result = runner.invoke(app, ["alerts", "list"])

    assert result.exit_code == 0
    assert "No active alerts" in result.stdout


@patch("kalshi_research.alerts.AlertMonitor")
def test_alerts_add_price(mock_monitor_cls: MagicMock) -> None:
    """Test adding a price alert."""
    mock_monitor = MagicMock()
    mock_monitor_cls.return_value = mock_monitor

    with patch("pathlib.Path.exists", return_value=False):
        result = runner.invoke(
            app, ["alerts", "add", "price", "TEST-TICKER", "--above", "60"]
        )

    assert result.exit_code == 0
    assert "Alert added" in result.stdout
    mock_monitor.add_condition.assert_called_once()


@patch("kalshi_research.alerts.AlertMonitor")
def test_alerts_add_volume(mock_monitor_cls: MagicMock) -> None:
    """Test adding a volume alert."""
    mock_monitor = MagicMock()
    mock_monitor_cls.return_value = mock_monitor

    with patch("pathlib.Path.exists", return_value=False):
        result = runner.invoke(
            app, ["alerts", "add", "volume", "TEST-TICKER", "--above", "10000"]
        )

    assert result.exit_code == 0
    assert "Alert added" in result.stdout


@patch("kalshi_research.alerts.AlertMonitor")
def test_alerts_add_spread(mock_monitor_cls: MagicMock) -> None:
    """Test adding a spread alert."""
    mock_monitor = MagicMock()
    mock_monitor_cls.return_value = mock_monitor

    with patch("pathlib.Path.exists", return_value=False):
        result = runner.invoke(
            app, ["alerts", "add", "spread", "TEST-TICKER", "--above", "5"]
        )

    assert result.exit_code == 0
    assert "Alert added" in result.stdout


@patch("kalshi_research.alerts.AlertMonitor")
def test_alerts_remove(mock_monitor_cls: MagicMock) -> None:
    """Test removing an alert."""
    mock_monitor = MagicMock()
    mock_monitor.remove_condition.return_value = True
    mock_monitor_cls.return_value = mock_monitor

    with patch("pathlib.Path.exists", return_value=False):
        result = runner.invoke(app, ["alerts", "remove", "alert-123"])

    assert result.exit_code == 0
    assert "removed" in result.stdout.lower()


@patch("kalshi_research.alerts.AlertMonitor")
def test_alerts_remove_not_found(mock_monitor_cls: MagicMock) -> None:
    """Test removing a non-existent alert."""
    mock_monitor = MagicMock()
    mock_monitor.remove_condition.return_value = False
    mock_monitor_cls.return_value = mock_monitor

    with patch("pathlib.Path.exists", return_value=False):
        result = runner.invoke(app, ["alerts", "remove", "nonexistent"])

    assert result.exit_code == 0
    assert "not found" in result.stdout.lower()


# ==================== Analysis CLI Tests ====================


@patch("kalshi_research.analysis.CalibrationAnalyzer")
@patch("kalshi_research.data.DatabaseManager")
def test_analysis_calibration(
    mock_db_cls: MagicMock, mock_analyzer_cls: MagicMock
) -> None:
    """Test calibration analysis."""
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    mock_db_cls.return_value = mock_db

    mock_analyzer = MagicMock()
    mock_result = MagicMock()
    mock_result.brier_score = 0.15
    mock_result.n_predictions = 100
    mock_analyzer.analyze.return_value = mock_result
    mock_analyzer_cls.return_value = mock_analyzer

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["analysis", "calibration"])

    assert result.exit_code == 0
    # Should show some calibration output
    assert any(
        x in result.stdout
        for x in ["Brier", "Calibration", "0.15", "100"]
    )


@patch("kalshi_research.data.DatabaseManager")
def test_analysis_metrics(mock_db_cls: MagicMock) -> None:
    """Test market metrics analysis."""
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    mock_db_cls.return_value = mock_db

    # Mock repository
    mock_repo = AsyncMock()
    mock_price = MagicMock()
    mock_price.yes_bid = 50
    mock_price.yes_ask = 52
    mock_price.volume_24h = 1000
    mock_repo.get_latest_price.return_value = mock_price
    mock_db.prices = mock_repo

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["analysis", "metrics", "TEST-TICKER"])

    assert result.exit_code == 0
    assert "TEST-TICKER" in result.stdout


# ==================== Research CLI Tests ====================


@patch("kalshi_research.research.ThesisTracker")
def test_research_thesis_create(mock_tracker_cls: MagicMock) -> None:
    """Test creating a thesis."""
    mock_tracker = MagicMock()
    mock_tracker_cls.return_value = mock_tracker

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
    mock_tracker.add_thesis.assert_called_once()


@patch("kalshi_research.research.ThesisTracker")
def test_research_thesis_list_empty(mock_tracker_cls: MagicMock) -> None:
    """Test listing theses when none exist."""
    mock_tracker = MagicMock()
    mock_tracker.list_theses.return_value = []
    mock_tracker_cls.return_value = mock_tracker

    result = runner.invoke(app, ["research", "thesis", "list"])

    assert result.exit_code == 0
    assert "No theses" in result.stdout


@patch("kalshi_research.research.ThesisTracker")
def test_research_thesis_list_with_theses(mock_tracker_cls: MagicMock) -> None:
    """Test listing theses."""
    mock_tracker = MagicMock()
    mock_thesis = MagicMock()
    mock_thesis.id = "thesis-1"
    mock_thesis.title = "Test Thesis"
    mock_thesis.status.value = "active"
    mock_thesis.edge_size = 0.2
    mock_tracker.list_theses.return_value = [mock_thesis]
    mock_tracker_cls.return_value = mock_tracker

    result = runner.invoke(app, ["research", "thesis", "list"])

    assert result.exit_code == 0
    assert "thesis-1" in result.stdout
    assert "Test Thesis" in result.stdout


@patch("kalshi_research.research.ThesisTracker")
def test_research_thesis_show(mock_tracker_cls: MagicMock) -> None:
    """Test showing a thesis."""
    mock_tracker = MagicMock()
    mock_thesis = MagicMock()
    mock_thesis.id = "thesis-1"
    mock_thesis.title = "Test Thesis"
    mock_thesis.status.value = "active"
    mock_thesis.your_probability = 0.7
    mock_thesis.market_probability = 0.5
    mock_thesis.confidence = 0.8
    mock_thesis.bull_case = "Bull case"
    mock_thesis.bear_case = "Bear case"
    mock_thesis.key_assumptions = ["Assumption 1"]
    mock_thesis.invalidation_criteria = ["Criterion 1"]
    mock_thesis.market_tickers = ["TICK1"]
    mock_thesis.updates = []
    mock_tracker.get_thesis.return_value = mock_thesis
    mock_tracker_cls.return_value = mock_tracker

    result = runner.invoke(app, ["research", "thesis", "show", "thesis-1"])

    assert result.exit_code == 0
    assert "Test Thesis" in result.stdout


@patch("kalshi_research.research.ThesisTracker")
def test_research_thesis_resolve(mock_tracker_cls: MagicMock) -> None:
    """Test resolving a thesis."""
    mock_tracker = MagicMock()
    mock_thesis = MagicMock()
    mock_tracker.get_thesis.return_value = mock_thesis
    mock_tracker_cls.return_value = mock_tracker

    result = runner.invoke(
        app, ["research", "thesis", "resolve", "thesis-1", "--outcome", "yes"]
    )

    assert result.exit_code == 0
    assert "resolved" in result.stdout.lower()
    mock_thesis.resolve.assert_called_once_with("yes")


@patch("kalshi_research.research.ThesisBacktester")
@patch("kalshi_research.data.DatabaseManager")
def test_research_backtest(
    mock_db_cls: MagicMock, mock_backtester_cls: MagicMock
) -> None:
    """Test running a backtest."""
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    mock_db_cls.return_value = mock_db

    mock_backtester = MagicMock()
    mock_result = MagicMock()
    mock_result.total_trades = 10
    mock_result.win_rate = 0.6
    mock_result.total_pnl = 150.0
    mock_result.sharpe_ratio = 1.5
    mock_backtester.run.return_value = mock_result
    mock_backtester_cls.return_value = mock_backtester

    with patch("pathlib.Path.exists", return_value=True):
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
    # Should show backtest results
    assert any(
        x in result.stdout
        for x in ["trades", "win", "pnl", "10", "60%"]
    )
