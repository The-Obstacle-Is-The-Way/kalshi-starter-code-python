from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from kalshi_research.cli import app

runner = CliRunner()


def test_alerts_list_empty() -> None:
    with runner.isolated_filesystem():
        alerts_file = Path("alerts.json")
        with patch("kalshi_research.cli.alerts._get_alerts_file", return_value=alerts_file):
            result = runner.invoke(app, ["alerts", "list"])

    assert result.exit_code == 0
    assert "No active alerts" in result.stdout


def test_alerts_add_price() -> None:
    with runner.isolated_filesystem():
        alerts_file = Path("alerts.json")
        with patch("kalshi_research.cli.alerts._get_alerts_file", return_value=alerts_file):
            result = runner.invoke(app, ["alerts", "add", "price", "TEST-TICKER", "--above", "60"])

        assert result.exit_code == 0
        assert "Alert added" in result.stdout
        stored = json.loads(alerts_file.read_text(encoding="utf-8"))
        assert len(stored["conditions"]) == 1


def test_alerts_add_volume() -> None:
    with runner.isolated_filesystem():
        alerts_file = Path("alerts.json")
        with patch("kalshi_research.cli.alerts._get_alerts_file", return_value=alerts_file):
            result = runner.invoke(
                app, ["alerts", "add", "volume", "TEST-TICKER", "--above", "10000"]
            )

        assert result.exit_code == 0
        assert "Alert added" in result.stdout
        stored = json.loads(alerts_file.read_text(encoding="utf-8"))
        assert len(stored["conditions"]) == 1


def test_alerts_add_spread() -> None:
    with runner.isolated_filesystem():
        alerts_file = Path("alerts.json")
        with patch("kalshi_research.cli.alerts._get_alerts_file", return_value=alerts_file):
            result = runner.invoke(app, ["alerts", "add", "spread", "TEST-TICKER", "--above", "5"])

        assert result.exit_code == 0
        assert "Alert added" in result.stdout
        stored = json.loads(alerts_file.read_text(encoding="utf-8"))
        assert len(stored["conditions"]) == 1


def test_alerts_add_sentiment() -> None:
    with runner.isolated_filesystem():
        alerts_file = Path("alerts.json")
        with patch("kalshi_research.cli.alerts._get_alerts_file", return_value=alerts_file):
            result = runner.invoke(
                app, ["alerts", "add", "sentiment", "TEST-TICKER", "--above", "0.2"]
            )

        assert result.exit_code == 0
        assert "Alert added" in result.stdout
        stored = json.loads(alerts_file.read_text(encoding="utf-8"))
        assert len(stored["conditions"]) == 1
        assert stored["conditions"][0]["condition_type"] == "sentiment_shift"


def test_alerts_add_volume_rejects_below() -> None:
    result = runner.invoke(app, ["alerts", "add", "volume", "TEST-TICKER", "--below", "1000"])
    assert result.exit_code == 1
    assert "volume alerts only support --above" in result.stdout


def test_alerts_add_spread_rejects_below() -> None:
    result = runner.invoke(app, ["alerts", "add", "spread", "TEST-TICKER", "--below", "5"])
    assert result.exit_code == 1
    assert "spread alerts only support --above" in result.stdout


def test_alerts_add_sentiment_rejects_below() -> None:
    result = runner.invoke(app, ["alerts", "add", "sentiment", "TEST-TICKER", "--below", "0.2"])
    assert result.exit_code == 1
    assert "sentiment alerts only support --above" in result.stdout


def test_alerts_remove() -> None:
    with runner.isolated_filesystem():
        alerts_file = Path("alerts.json")
        alerts_file.write_text(
            json.dumps({"conditions": [{"id": "alert-12345678", "label": "test alert"}]}),
            encoding="utf-8",
        )
        with patch("kalshi_research.cli.alerts._get_alerts_file", return_value=alerts_file):
            result = runner.invoke(app, ["alerts", "remove", "alert-123"])

        assert result.exit_code == 0
        assert "removed" in result.stdout.lower()
        stored = json.loads(alerts_file.read_text(encoding="utf-8"))
        assert stored["conditions"] == []


def test_alerts_remove_not_found() -> None:
    with runner.isolated_filesystem():
        alerts_file = Path("alerts.json")
        with patch("kalshi_research.cli.alerts._get_alerts_file", return_value=alerts_file):
            result = runner.invoke(app, ["alerts", "remove", "nonexistent"])

    assert result.exit_code == 0
    assert "not found" in result.stdout.lower()


def test_alerts_list_invalid_json_exits_with_error(tmp_path: Path) -> None:
    alerts_file = tmp_path / "alerts.json"
    alerts_file.write_text("{not json", encoding="utf-8")

    with patch("kalshi_research.cli.alerts._get_alerts_file", return_value=alerts_file):
        result = runner.invoke(app, ["alerts", "list"])

    assert result.exit_code == 1
    assert "Alerts file is not valid JSON" in result.stdout


@patch("kalshi_research.cli.alerts._load_alerts")
@patch("kalshi_research.api.KalshiPublicClient")
def test_alerts_monitor_once_exits(
    mock_client_cls: MagicMock,
    mock_load_alerts: MagicMock,
) -> None:
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


@patch("kalshi_research.cli.alerts._load_alerts")
@patch("kalshi_research.api.KalshiPublicClient")
def test_alerts_monitor_continuous_shows_ctrl_c(
    mock_client_cls: MagicMock,
    mock_load_alerts: MagicMock,
) -> None:
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

    with patch(
        "kalshi_research.cli.alerts.asyncio.sleep", new=AsyncMock(side_effect=KeyboardInterrupt)
    ):
        result = runner.invoke(app, ["alerts", "monitor", "--interval", "1"])

    assert result.exit_code == 0
    assert "Press Ctrl+C" in result.stdout


def test_alerts_monitor_daemon_calls_spawn() -> None:
    with (
        patch("kalshi_research.cli.alerts._load_alerts", return_value={"conditions": [{}]}),
        patch(
            "kalshi_research.cli.alerts._spawn_alert_monitor_daemon",
            return_value=(12345, Path("data/alert_monitor.log")),
        ) as mock_spawn,
    ):
        result = runner.invoke(
            app, ["--env", "demo", "alerts", "monitor", "--daemon", "--interval", "5"]
        )

    assert result.exit_code == 0
    assert "Alert monitor started in background" in result.stdout
    mock_spawn.assert_called_once()
    assert mock_spawn.call_args.kwargs["environment"] == "demo"
    assert mock_spawn.call_args.kwargs["interval"] == 5


@patch("kalshi_research.cli.alerts._load_alerts")
@patch("kalshi_research.cli.alerts.subprocess.Popen")
def test_alerts_monitor_daemon_spawns_background_process(
    mock_popen: MagicMock,
    mock_load_alerts: MagicMock,
) -> None:
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
        patch("kalshi_research.cli.alerts.sys.executable", "/usr/bin/python"),
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


@patch("kalshi_research.cli.alerts._load_alerts")
@patch("kalshi_research.cli.alerts.subprocess.Popen")
def test_alerts_monitor_daemon_does_not_spawn_without_alerts(
    mock_popen: MagicMock,
    mock_load_alerts: MagicMock,
) -> None:
    mock_load_alerts.return_value = {"conditions": []}

    result = runner.invoke(app, ["alerts", "monitor", "--daemon", "--interval", "5"])

    assert result.exit_code == 0
    assert "No alerts configured" in result.stdout
    mock_popen.assert_not_called()
