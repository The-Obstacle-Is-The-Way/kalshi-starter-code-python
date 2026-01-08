"""Extended CLI tests for alerts, analysis, and research commands."""

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

from typer.testing import CliRunner

from kalshi_research.cli import app

runner = CliRunner()


# ==================== Alerts CLI Tests ====================


def test_alerts_list_empty() -> None:
    """Test listing alerts when none exist."""
    with runner.isolated_filesystem():
        alerts_file = Path("alerts.json")
        with patch("kalshi_research.cli._get_alerts_file", return_value=alerts_file):
            result = runner.invoke(app, ["alerts", "list"])

    assert result.exit_code == 0
    assert "No active alerts" in result.stdout


def test_alerts_add_price() -> None:
    """Test adding a price alert."""
    with runner.isolated_filesystem():
        alerts_file = Path("alerts.json")
        with patch("kalshi_research.cli._get_alerts_file", return_value=alerts_file):
            result = runner.invoke(app, ["alerts", "add", "price", "TEST-TICKER", "--above", "60"])

        assert result.exit_code == 0
        assert "Alert added" in result.stdout
        stored = json.loads(alerts_file.read_text(encoding="utf-8"))
        assert len(stored["conditions"]) == 1


def test_alerts_add_volume() -> None:
    """Test adding a volume alert."""
    with runner.isolated_filesystem():
        alerts_file = Path("alerts.json")
        with patch("kalshi_research.cli._get_alerts_file", return_value=alerts_file):
            result = runner.invoke(
                app, ["alerts", "add", "volume", "TEST-TICKER", "--above", "10000"]
            )

        assert result.exit_code == 0
        assert "Alert added" in result.stdout
        stored = json.loads(alerts_file.read_text(encoding="utf-8"))
        assert len(stored["conditions"]) == 1


def test_alerts_add_spread() -> None:
    """Test adding a spread alert."""
    with runner.isolated_filesystem():
        alerts_file = Path("alerts.json")
        with patch("kalshi_research.cli._get_alerts_file", return_value=alerts_file):
            result = runner.invoke(app, ["alerts", "add", "spread", "TEST-TICKER", "--above", "5"])

        assert result.exit_code == 0
        assert "Alert added" in result.stdout
        stored = json.loads(alerts_file.read_text(encoding="utf-8"))
        assert len(stored["conditions"]) == 1


def test_alerts_remove() -> None:
    """Test removing an alert."""
    with runner.isolated_filesystem():
        alerts_file = Path("alerts.json")
        alerts_file.write_text(
            json.dumps({"conditions": [{"id": "alert-12345678", "label": "test alert"}]}),
            encoding="utf-8",
        )
        with patch("kalshi_research.cli._get_alerts_file", return_value=alerts_file):
            result = runner.invoke(app, ["alerts", "remove", "alert-123"])

        assert result.exit_code == 0
        assert "removed" in result.stdout.lower()
        stored = json.loads(alerts_file.read_text(encoding="utf-8"))
        assert stored["conditions"] == []


def test_alerts_remove_not_found() -> None:
    """Test removing a non-existent alert."""
    with runner.isolated_filesystem():
        alerts_file = Path("alerts.json")
        with patch("kalshi_research.cli._get_alerts_file", return_value=alerts_file):
            result = runner.invoke(app, ["alerts", "remove", "nonexistent"])

    assert result.exit_code == 0
    assert "not found" in result.stdout.lower()


@patch("kalshi_research.cli._load_alerts")
@patch("kalshi_research.api.KalshiPublicClient")
def test_alerts_monitor_once_exits(
    mock_client_cls: MagicMock,
    mock_load_alerts: MagicMock,
) -> None:
    """--once mode should exit after single check with correct messaging."""
    mock_load_alerts.return_value = {
        "conditions": [
            {
                "id": "alert-123",
                "condition_type": "price_above",
                "ticker": "TEST-TICKER",
                "threshold": 0.9,
                "label": "price_above TEST-TICKER > 0.9",
            }
        ]
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    mock_market = MagicMock()
    mock_market.ticker = "TEST-TICKER"
    mock_market.title = "Test Market"
    mock_market.yes_bid = 50
    mock_market.yes_ask = 52
    mock_market.volume = 1000

    async def market_gen(status=None, max_pages: int | None = None):
        yield mock_market

    mock_client.get_all_markets = MagicMock(side_effect=market_gen)

    result = runner.invoke(app, ["alerts", "monitor", "--once"])

    assert result.exit_code == 0
    assert "Press Ctrl+C" not in result.stdout
    assert "Running single check" in result.stdout
    assert "Fetching markets" in result.stdout
    assert "Single check complete" in result.stdout


@patch("kalshi_research.cli._load_alerts")
@patch("kalshi_research.api.KalshiPublicClient")
def test_alerts_monitor_continuous_shows_ctrl_c(
    mock_client_cls: MagicMock,
    mock_load_alerts: MagicMock,
) -> None:
    """Continuous mode should show Ctrl+C message."""
    mock_load_alerts.return_value = {
        "conditions": [
            {
                "id": "alert-123",
                "condition_type": "price_above",
                "ticker": "TEST-TICKER",
                "threshold": 0.9,
                "label": "price_above TEST-TICKER > 0.9",
            }
        ]
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    mock_market = MagicMock()
    mock_market.ticker = "TEST-TICKER"
    mock_market.title = "Test Market"
    mock_market.yes_bid = 50
    mock_market.yes_ask = 52
    mock_market.volume = 1000

    async def market_gen(status=None, max_pages: int | None = None):
        yield mock_market

    mock_client.get_all_markets = MagicMock(side_effect=market_gen)

    with patch("kalshi_research.cli.asyncio.sleep", new=AsyncMock(side_effect=KeyboardInterrupt)):
        result = runner.invoke(app, ["alerts", "monitor", "--interval", "1"])

    assert result.exit_code == 0
    assert "Press Ctrl+C" in result.stdout


@patch("kalshi_research.cli._load_alerts")
@patch("kalshi_research.cli.subprocess.Popen")
def test_alerts_monitor_daemon_spawns_background_process(
    mock_popen: MagicMock,
    mock_load_alerts: MagicMock,
) -> None:
    """--daemon should spawn a detached process and exit immediately."""
    mock_load_alerts.return_value = {
        "conditions": [
            {
                "id": "alert-123",
                "condition_type": "price_above",
                "ticker": "TEST-TICKER",
                "threshold": 0.9,
                "label": "price_above TEST-TICKER > 0.9",
            }
        ]
    }

    mock_proc = MagicMock()
    mock_proc.pid = 4242
    mock_popen.return_value = mock_proc

    with (
        runner.isolated_filesystem(),
        patch("kalshi_research.cli.sys.executable", "/usr/bin/python"),
    ):
        result = runner.invoke(
            app,
            [
                "alerts",
                "monitor",
                "--daemon",
                "--interval",
                "5",
                "--max-pages",
                "2",
                "--once",
            ],
        )

    assert result.exit_code == 0
    assert "PID" in result.stdout
    assert "alert_monitor.log" in result.stdout

    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    assert args[0][:4] == ["/usr/bin/python", "-m", "kalshi_research.cli", "alerts"]
    assert args[0][4:6] == ["monitor", "--interval"]
    assert "--daemon" not in args[0]
    assert kwargs["stdin"] is not None
    assert kwargs["stdout"] is kwargs["stderr"]
    assert "env" in kwargs
    assert kwargs["env"]["KALSHI_ENVIRONMENT"] in {"demo", "prod"}
    assert kwargs.get("start_new_session") is True or kwargs.get("creationflags", 0) != 0


@patch("kalshi_research.cli._load_alerts")
@patch("kalshi_research.cli.subprocess.Popen")
def test_alerts_monitor_daemon_does_not_spawn_without_alerts(
    mock_popen: MagicMock,
    mock_load_alerts: MagicMock,
) -> None:
    """--daemon should not spawn when there are no configured alerts."""
    mock_load_alerts.return_value = {"conditions": []}

    result = runner.invoke(app, ["alerts", "monitor", "--daemon", "--interval", "5"])

    assert result.exit_code == 0
    assert "No alerts configured" in result.stdout
    mock_popen.assert_not_called()


# ==================== Analysis CLI Tests ====================


# ==================== Scan CLI Tests ====================


@patch("kalshi_research.data.repositories.PriceRepository")
@patch("kalshi_research.data.DatabaseManager")
@patch("kalshi_research.api.KalshiPublicClient")
def test_scan_movers_uses_probability_units(
    mock_client_cls: MagicMock,
    mock_db_cls: MagicMock,
    mock_price_repo_cls: MagicMock,
) -> None:
    """`scan movers` should treat snapshot midpoints as probabilities (not raw cents)."""
    from datetime import UTC, datetime, timedelta

    from kalshi_research.data.models import PriceSnapshot

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    mock_market = MagicMock()
    mock_market.ticker = "TEST-TICKER"
    mock_market.title = "Test Market"
    mock_market.volume = 1000

    async def market_gen(status=None, max_pages: int | None = None):
        yield mock_market

    mock_client.get_all_markets = MagicMock(side_effect=market_gen)

    now = datetime.now(UTC)
    newest = PriceSnapshot(
        ticker="TEST-TICKER",
        snapshot_time=now,
        yes_bid=51,
        yes_ask=53,  # midpoint = 52c -> 52.0%
        no_bid=47,
        no_ask=49,
        last_price=52,
        volume=100,
        volume_24h=10,
        open_interest=20,
        liquidity=1000,
    )
    oldest = PriceSnapshot(
        ticker="TEST-TICKER",
        snapshot_time=now - timedelta(hours=1),
        yes_bid=49,
        yes_ask=51,  # midpoint = 50c -> 50.0%
        no_bid=49,
        no_ask=51,
        last_price=50,
        volume=100,
        volume_24h=10,
        open_interest=20,
        liquidity=1000,
    )

    mock_price_repo = MagicMock()
    mock_price_repo.get_for_market = AsyncMock(return_value=[newest, oldest])
    mock_price_repo_cls.return_value = mock_price_repo

    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session_cm
    mock_session_cm.__aexit__.return_value = False

    mock_db_cm = AsyncMock()
    mock_db_cm.__aenter__.return_value = mock_db_cm
    mock_db_cm.__aexit__.return_value = False
    mock_db_cm.session_factory = MagicMock(return_value=mock_session_cm)
    mock_db_cls.return_value = mock_db_cm

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["scan", "movers", "--period", "24h", "--top", "1"])

    assert result.exit_code == 0
    assert "50.0% → 52.0%" in result.stdout
    assert "2.0%" in result.stdout


@patch("kalshi_research.data.repositories.PriceRepository")
@patch("kalshi_research.data.DatabaseManager")
@patch("kalshi_research.api.KalshiPublicClient")
def test_scan_arbitrage_warns_when_tickers_truncated(
    mock_client_cls: MagicMock,
    mock_db_cls: MagicMock,
    mock_price_repo_cls: MagicMock,
) -> None:
    """`scan arbitrage` should warn when correlation analysis is truncated for performance."""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    m1 = MagicMock()
    m1.ticker = "T1"
    m1.event_ticker = "E1"
    m1.title = "Market 1"
    m1.yes_bid = 50
    m1.yes_ask = 52

    m2 = MagicMock()
    m2.ticker = "T2"
    m2.event_ticker = "E2"
    m2.title = "Market 2"
    m2.yes_bid = 48
    m2.yes_ask = 50

    async def market_gen(status=None, max_pages: int | None = None):
        yield m1
        yield m2

    mock_client.get_all_markets = MagicMock(side_effect=market_gen)

    mock_price_repo = MagicMock()
    mock_price_repo.get_for_market = AsyncMock(return_value=[])
    mock_price_repo_cls.return_value = mock_price_repo

    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session_cm
    mock_session_cm.__aexit__.return_value = False

    mock_db_cm = AsyncMock()
    mock_db_cm.__aenter__.return_value = mock_db_cm
    mock_db_cm.__aexit__.return_value = False
    mock_db_cm.session_factory = MagicMock(return_value=mock_session_cm)
    mock_db_cls.return_value = mock_db_cm

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["scan", "arbitrage", "--tickers-limit", "1"])

    assert result.exit_code == 0
    assert "Limiting correlation analysis to first 1 tickers" in result.stdout


@patch("kalshi_research.analysis.CalibrationAnalyzer")
@patch("kalshi_research.data.DatabaseManager")
def test_analysis_calibration(mock_db_cls: MagicMock, mock_analyzer_cls: MagicMock) -> None:
    """Test calibration analysis."""
    from datetime import UTC, datetime

    # Mock session context manager
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session_cm
    mock_session_cm.__aexit__.return_value = False

    mock_session_factory = MagicMock(return_value=mock_session_cm)

    # Mock db context manager
    mock_db_cm = AsyncMock()
    mock_db_cm.__aenter__.return_value = mock_db_cm
    mock_db_cm.__aexit__.return_value = False
    mock_db_cm.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db_cm

    settlement = MagicMock()
    settlement.ticker = "TEST-TICKER"
    settlement.result = "yes"
    settlement.settled_at = datetime.now(UTC)

    mock_settlement_repo = MagicMock()
    mock_settlement_repo.get_settled_after = AsyncMock(return_value=[settlement])

    snapshot = MagicMock()
    snapshot.midpoint = 60

    mock_price_repo = MagicMock()
    mock_price_repo.get_for_market = AsyncMock(return_value=[snapshot])

    mock_result = MagicMock()
    mock_result.brier_score = 0.15
    mock_result.n_samples = 1
    mock_result.brier_skill_score = 0.4
    mock_result.resolution = 0.1
    mock_result.reliability = 0.05
    mock_result.uncertainty = 0.2

    mock_analyzer = MagicMock()
    mock_analyzer.compute_calibration.return_value = mock_result
    mock_analyzer_cls.return_value = mock_analyzer

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch(
            "kalshi_research.data.repositories.SettlementRepository",
            return_value=mock_settlement_repo,
        ),
        patch(
            "kalshi_research.data.repositories.PriceRepository",
            return_value=mock_price_repo,
        ),
    ):
        result = runner.invoke(app, ["analysis", "calibration"])

    assert result.exit_code == 0
    assert "Brier" in result.stdout or "0.15" in result.stdout


@patch("kalshi_research.data.DatabaseManager")
def test_analysis_metrics(mock_db_cls: MagicMock) -> None:
    """Test market metrics analysis."""
    # Mock price data
    mock_price = MagicMock()
    mock_price.yes_bid = 0
    mock_price.yes_ask = 2
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

    spread_row = next(line for line in result.stdout.splitlines() if "Spread" in line)
    assert "2¢" in spread_row


# ==================== Research CLI Tests ====================


def test_research_thesis_create() -> None:
    """Test creating a thesis."""
    with runner.isolated_filesystem():
        thesis_file = Path("theses.json")
        with patch("kalshi_research.cli._get_thesis_file", return_value=thesis_file):
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
    """Test listing theses when none exist."""
    with runner.isolated_filesystem():
        thesis_file = Path("theses.json")
        with patch("kalshi_research.cli._get_thesis_file", return_value=thesis_file):
            result = runner.invoke(app, ["research", "thesis", "list"])

    assert result.exit_code == 0
    assert "No theses" in result.stdout


def test_research_thesis_list_with_theses() -> None:
    """Test listing theses."""
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
        with patch("kalshi_research.cli._get_thesis_file", return_value=thesis_file):
            result = runner.invoke(app, ["research", "thesis", "list"])

    assert result.exit_code == 0
    # Check for either the full ID or the shortened version
    assert "thesis-" in result.stdout.lower() or "Test Thesis" in result.stdout


def test_research_thesis_show() -> None:
    """Test showing a thesis."""
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
        with patch("kalshi_research.cli._get_thesis_file", return_value=thesis_file):
            result = runner.invoke(app, ["research", "thesis", "show", "thesis-1"])

    assert result.exit_code == 0
    assert "Test Thesis" in result.stdout


def test_research_thesis_resolve() -> None:
    """Test resolving a thesis."""
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
        with patch("kalshi_research.cli._get_thesis_file", return_value=thesis_file):
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


# ==================== Portfolio CLI Tests ====================


@patch("kalshi_research.api.KalshiClient")
def test_portfolio_balance_loads_dotenv(mock_client_cls: MagicMock) -> None:
    """Portfolio commands should read auth config from .env during CLI invocation."""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get_balance = AsyncMock(return_value={"available": 123})
    mock_client_cls.return_value = mock_client

    with runner.isolated_filesystem():
        Path(".env").write_text(
            "\n".join(
                [
                    "KALSHI_KEY_ID=test-key-id",
                    "KALSHI_PRIVATE_KEY_B64=test-private-key-b64",
                    "KALSHI_ENVIRONMENT=demo",
                    "",
                ]
            )
        )

        with patch.dict(os.environ, {}, clear=True):
            result = runner.invoke(app, ["portfolio", "balance"])

    assert result.exit_code == 0
    assert "Account Balance" in result.stdout


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
def test_portfolio_positions_shows_zero_mark_price(mock_db_cls: MagicMock) -> None:
    """0-valued mark prices should render as `0¢` (not `-`)."""
    mock_position = MagicMock()
    mock_position.ticker = "TEST-TICKER"
    mock_position.side = "yes"
    mock_position.quantity = 1
    mock_position.avg_price_cents = 10
    mock_position.current_price_cents = 0
    mock_position.unrealized_pnl_cents = 0
    mock_position.closed_at = None

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_position]

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    mock_db = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db.close = AsyncMock()
    mock_db_cls.return_value = mock_db

    result = runner.invoke(app, ["portfolio", "positions"])

    assert result.exit_code == 0
    assert "0¢" in result.stdout


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
