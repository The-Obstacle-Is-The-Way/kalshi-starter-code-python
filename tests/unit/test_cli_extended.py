"""Extended CLI tests for alerts, analysis, and research commands."""

import json
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

from typer.testing import CliRunner

from kalshi_research.cli import app

runner = CliRunner()


# ==================== Alerts CLI Tests ====================


def test_alerts_list_empty() -> None:
    """Test listing alerts when none exist."""
    with patch("pathlib.Path.exists", return_value=False):
        result = runner.invoke(app, ["alerts", "list"])

    assert result.exit_code == 0
    assert "No active alerts" in result.stdout


def test_alerts_add_price() -> None:
    """Test adding a price alert."""
    mock_file = mock_open(read_data='{"conditions": []}')

    with (
        patch("pathlib.Path.exists", return_value=False),
        patch("builtins.open", mock_file),
        patch("pathlib.Path.mkdir"),
    ):
        result = runner.invoke(app, ["alerts", "add", "price", "TEST-TICKER", "--above", "60"])

    assert result.exit_code == 0
    assert "Alert added" in result.stdout


def test_alerts_add_volume() -> None:
    """Test adding a volume alert."""
    mock_file = mock_open(read_data='{"conditions": []}')

    with (
        patch("pathlib.Path.exists", return_value=False),
        patch("builtins.open", mock_file),
        patch("pathlib.Path.mkdir"),
    ):
        result = runner.invoke(app, ["alerts", "add", "volume", "TEST-TICKER", "--above", "10000"])

    assert result.exit_code == 0
    assert "Alert added" in result.stdout


def test_alerts_add_spread() -> None:
    """Test adding a spread alert."""
    mock_file = mock_open(read_data='{"conditions": []}')

    with (
        patch("pathlib.Path.exists", return_value=False),
        patch("builtins.open", mock_file),
        patch("pathlib.Path.mkdir"),
    ):
        result = runner.invoke(app, ["alerts", "add", "spread", "TEST-TICKER", "--above", "5"])

    assert result.exit_code == 0
    assert "Alert added" in result.stdout


def test_alerts_remove() -> None:
    """Test removing an alert."""
    alert_data = {"conditions": [{"id": "alert-12345678", "label": "test alert"}]}
    mock_file = mock_open(read_data=json.dumps(alert_data))

    with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.open", mock_file):
        result = runner.invoke(app, ["alerts", "remove", "alert-123"])

    assert result.exit_code == 0
    assert "removed" in result.stdout.lower()


def test_alerts_remove_not_found() -> None:
    """Test removing a non-existent alert."""
    with patch("pathlib.Path.exists", return_value=False):
        result = runner.invoke(app, ["alerts", "remove", "nonexistent"])

    assert result.exit_code == 0
    assert "not found" in result.stdout.lower()


# ==================== Analysis CLI Tests ====================


@patch("kalshi_research.analysis.CalibrationAnalyzer")
@patch("kalshi_research.data.DatabaseManager")
def test_analysis_calibration(mock_db_cls: MagicMock, mock_analyzer_cls: MagicMock) -> None:
    """Test calibration analysis."""
    # Mock session
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()

    # Mock session factory
    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    # Mock db
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    mock_analyzer = MagicMock()
    mock_result = MagicMock()
    mock_result.brier_score = 0.15
    mock_result.n_predictions = 100
    mock_result.resolution = 0.1
    mock_result.reliability = 0.05
    mock_result.uncertainty = 0.2
    mock_result.bins = []

    # Make analyze return a coroutine
    async def mock_analyze(**kwargs):
        return mock_result

    mock_analyzer.analyze = mock_analyze
    mock_analyzer_cls.return_value = mock_analyzer

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["analysis", "calibration"])

    assert result.exit_code == 0
    assert "Brier" in result.stdout or "0.15" in result.stdout


@patch("kalshi_research.data.DatabaseManager")
def test_analysis_metrics(mock_db_cls: MagicMock) -> None:
    """Test market metrics analysis."""
    # Mock price data
    mock_price = MagicMock()
    mock_price.yes_bid = 50
    mock_price.yes_ask = 52
    mock_price.no_bid = 48
    mock_price.no_ask = 50
    mock_price.volume_24h = 1000
    mock_price.open_interest = 500

    # Mock the prices repository with async get_latest
    async def mock_get_latest(ticker):
        return mock_price

    mock_prices_repo = MagicMock()
    mock_prices_repo.get_latest = mock_get_latest

    # Mock session
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()

    # Mock session factory
    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    # Mock db
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    # Patch PriceRepository to return our mock
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("kalshi_research.data.repositories.PriceRepository", return_value=mock_prices_repo),
    ):
        result = runner.invoke(app, ["analysis", "metrics", "TEST-TICKER"])

    assert result.exit_code == 0
    assert "TEST-TICKER" in result.stdout


# ==================== Research CLI Tests ====================


def test_research_thesis_create() -> None:
    """Test creating a thesis."""
    mock_file = mock_open(read_data='{"theses": []}')

    with patch("builtins.open", mock_file), patch("pathlib.Path.mkdir"):
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


def test_research_thesis_list_empty() -> None:
    """Test listing theses when none exist."""
    with patch("pathlib.Path.exists", return_value=False):
        result = runner.invoke(app, ["research", "thesis", "list"])

    assert result.exit_code == 0
    assert "No theses" in result.stdout


def test_research_thesis_list_with_theses() -> None:
    """Test listing theses."""
    thesis_data = {
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
    mock_file = mock_open(read_data=json.dumps(thesis_data))

    with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.open", mock_file):
        result = runner.invoke(app, ["research", "thesis", "list"])

    assert result.exit_code == 0
    # Check for either the full ID or the shortened version
    assert "thesis-" in result.stdout.lower() or "Test Thesis" in result.stdout


def test_research_thesis_show() -> None:
    """Test showing a thesis."""
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
                "market_tickers": ["TICK1"],
                "updates": [],
            }
        ]
    }
    mock_file = mock_open(read_data=json.dumps(thesis_data))

    with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.open", mock_file):
        result = runner.invoke(app, ["research", "thesis", "show", "thesis-1"])

    assert result.exit_code == 0
    assert "Test Thesis" in result.stdout


def test_research_thesis_resolve() -> None:
    """Test resolving a thesis."""
    thesis_data = {
        "theses": [
            {
                "id": "thesis-12345678",
                "title": "Test Thesis",
                "status": "active",
            }
        ]
    }
    mock_file = mock_open(read_data=json.dumps(thesis_data))

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.open", mock_file),
        patch("pathlib.Path.mkdir"),
    ):
        result = runner.invoke(
            app, ["research", "thesis", "resolve", "thesis-1", "--outcome", "yes"]
        )

    assert result.exit_code == 0
    assert "resolved" in result.stdout.lower()


@patch("kalshi_research.data.DatabaseManager")
def test_research_backtest(mock_db_cls: MagicMock) -> None:
    """Test running a backtest."""
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = AsyncMock()
    mock_db_cls.return_value = mock_db

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
    # Should show some backtest output (even if placeholder)
    assert "Backtest" in result.stdout or "trades" in result.stdout.lower()


# ==================== Portfolio-Thesis Link Tests (BUG-010) ====================


@patch("kalshi_research.data.DatabaseManager")
def test_portfolio_link_success(mock_db_cls: MagicMock) -> None:
    """Test linking a position to a thesis."""
    # Mock position
    mock_position = MagicMock()
    mock_position.ticker = "TEST-TICKER"
    mock_position.thesis_id = None

    # Mock async session and query execution
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_position

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    # Mock session factory
    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    # Mock db
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["portfolio", "link", "TEST-TICKER", "--thesis", "thesis-123"])

    assert result.exit_code == 0
    assert "linked" in result.stdout.lower()


@patch("kalshi_research.data.DatabaseManager")
def test_portfolio_link_position_not_found(mock_db_cls: MagicMock) -> None:
    """Test linking when position doesn't exist."""
    # Mock async session and query execution returning None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Mock session factory
    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    # Mock db
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["portfolio", "link", "NONEXISTENT", "--thesis", "thesis-123"])

    assert result.exit_code == 0
    assert "not found" in result.stdout.lower() or "no open position" in result.stdout.lower()


@patch("kalshi_research.data.DatabaseManager")
def test_portfolio_suggest_links_with_matches(mock_db_cls: MagicMock) -> None:
    """Test suggesting links when there are matching tickers."""
    # Mock position without thesis
    mock_position = MagicMock()
    mock_position.ticker = "SENATE-2024"
    mock_position.thesis_id = None

    # Mock async session and query execution
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_position]

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Mock session factory
    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    # Mock db
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    # Mock theses data
    thesis_data = {
        "theses": [
            {
                "id": "thesis-12345678",
                "title": "Senate Control",
                "market_tickers": ["SENATE-2024"],
                "status": "active",
            }
        ]
    }
    mock_file = mock_open(read_data=json.dumps(thesis_data))

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.open", mock_file),
    ):
        result = runner.invoke(app, ["portfolio", "suggest-links"])

    assert result.exit_code == 0
    assert "suggest" in result.stdout.lower() or "SENATE-2024" in result.stdout


@patch("kalshi_research.data.DatabaseManager")
def test_portfolio_suggest_links_no_matches(mock_db_cls: MagicMock) -> None:
    """Test suggesting links when there are no matches."""
    # Mock async session and query execution returning empty list
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Mock session factory
    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    # Mock db
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    with patch("pathlib.Path.exists", return_value=False):
        result = runner.invoke(app, ["portfolio", "suggest-links"])

    assert result.exit_code == 0
    assert "no" in result.stdout.lower() or "not found" in result.stdout.lower()


@patch("kalshi_research.data.DatabaseManager")
def test_research_thesis_show_with_positions(mock_db_cls: MagicMock) -> None:
    """Test showing a thesis with linked positions."""
    # Mock position linked to thesis
    mock_position = MagicMock()
    mock_position.ticker = "TEST-TICKER"
    mock_position.side = "yes"
    mock_position.quantity = 100
    mock_position.avg_price_cents = 55
    mock_position.unrealized_pnl_cents = 500

    # Mock async session and query execution
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_position]

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Mock session factory
    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    # Mock db
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    # Mock thesis data
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
    # Should show position info when --with-positions is used
    assert "position" in result.stdout.lower() or "TEST-TICKER" in result.stdout
