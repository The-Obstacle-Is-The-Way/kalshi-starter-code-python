from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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


def test_alerts_add_price_above_zero_is_above() -> None:
    with runner.isolated_filesystem():
        alerts_file = Path("alerts.json")
        with patch("kalshi_research.cli.alerts._get_alerts_file", return_value=alerts_file):
            result = runner.invoke(app, ["alerts", "add", "price", "TEST-TICKER", "--above", "0"])

        assert result.exit_code == 0
        stored = json.loads(alerts_file.read_text(encoding="utf-8"))
        assert stored["conditions"][0]["condition_type"] == "price_above"


def test_alerts_add_rejects_both_above_and_below() -> None:
    result = runner.invoke(
        app,
        ["alerts", "add", "price", "TEST-TICKER", "--above", "60", "--below", "40"],
    )
    assert result.exit_code == 1
    assert "Specify only one of --above or --below" in result.stdout


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
    """Removing a non-existent alert should return exit code 2 (not found)."""
    with runner.isolated_filesystem():
        alerts_file = Path("alerts.json")
        with patch("kalshi_research.cli.alerts._get_alerts_file", return_value=alerts_file):
            result = runner.invoke(app, ["alerts", "remove", "nonexistent"])

    assert result.exit_code == 2  # Unix convention: 2 = not found / usage error
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
    mock_market.midpoint = 51.0
    mock_market.volume = 1000

    async def market_gen(status=None, max_pages: int | None = None, mve_filter=None):
        del mve_filter
        yield mock_market

    mock_client.get_all_markets = MagicMock(side_effect=market_gen)

    result = runner.invoke(app, ["alerts", "monitor", "--once"])

    assert result.exit_code == 0
    assert "Press Ctrl+C" not in result.stdout
    assert "Running single check" in result.stdout
    assert "Fetching markets" in result.stdout
    assert "Single check complete" in result.stdout


@pytest.mark.asyncio
async def test_alert_monitor_loop_prints_utc_timestamp_when_alerts_trigger(monkeypatch) -> None:
    """Triggered alerts should display a timezone-aware UTC timestamp."""
    import kalshi_research.api as api_module
    from kalshi_research.cli import alerts as alerts_cli

    printed: list[str] = []

    def fake_print(*args, **kwargs) -> None:
        del kwargs
        if args:
            printed.append(str(args[0]))

    monkeypatch.setattr(alerts_cli.console, "print", fake_print)

    class DummyClient:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        async def __aenter__(self) -> DummyClient:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        async def get_all_markets(self, *args, **kwargs):
            del args, kwargs
            if False:  # pragma: no cover
                yield None

    monkeypatch.setattr(api_module, "KalshiPublicClient", DummyClient)

    class DummyMonitor:
        def list_conditions(self) -> list[object]:
            return []

        async def check_conditions(self, *args, **kwargs) -> list[object]:
            del args, kwargs
            return [object()]

    await alerts_cli._run_alert_monitor_loop(
        interval=1,
        once=True,
        max_pages=None,
        monitor=DummyMonitor(),
    )

    triggered_lines = [line for line in printed if "triggered at" in line]
    assert triggered_lines
    assert "+00:00" in triggered_lines[0]


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
    mock_market.midpoint = 51.0
    mock_market.volume = 1000

    async def market_gen(status=None, max_pages: int | None = None, mve_filter=None):
        del mve_filter
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
def test_alerts_monitor_adds_optional_notifiers(mock_load_alerts: MagicMock) -> None:
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

    monitor = MagicMock()

    with (
        patch("kalshi_research.alerts.AlertMonitor", return_value=monitor),
        patch(
            "kalshi_research.cli.alerts._run_alert_monitor_loop",
            new=AsyncMock(return_value=None),
        ),
        patch("kalshi_research.alerts.notifiers.ConsoleNotifier") as mock_console_notifier,
        patch("kalshi_research.alerts.notifiers.FileNotifier") as mock_file_notifier,
        patch("kalshi_research.alerts.notifiers.WebhookNotifier") as mock_webhook_notifier,
    ):
        result = runner.invoke(
            app,
            [
                "alerts",
                "monitor",
                "--once",
                "--output-file",
                "alerts.jsonl",
                "--webhook-url",
                "https://example.com/webhook",
            ],
        )

    assert result.exit_code == 0
    mock_console_notifier.assert_called_once_with()
    mock_file_notifier.assert_called_once_with(Path("alerts.jsonl"))
    mock_webhook_notifier.assert_called_once_with("https://example.com/webhook")

    monitor.add_notifier.assert_any_call(mock_console_notifier.return_value)
    monitor.add_notifier.assert_any_call(mock_file_notifier.return_value)
    monitor.add_notifier.assert_any_call(mock_webhook_notifier.return_value)


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
                "--output-file",
                "alerts.jsonl",
                "--webhook-url",
                "https://example.com/webhook",
            ],
        )

    assert result.exit_code == 0
    assert "PID" in result.stdout
    assert "alert_monitor.log" in result.stdout

    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    assert args[0][:4] == ["/usr/bin/python", "-m", "kalshi_research.cli", "alerts"]
    assert args[0][4:6] == ["monitor", "--interval"]
    assert "--output-file" in args[0]
    assert "alerts.jsonl" in args[0]
    assert "--webhook-url" in args[0]
    assert "https://example.com/webhook" in args[0]
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


def test_alert_monitor_daemon_log_lock_inherited(tmp_path: Path, monkeypatch) -> None:
    if sys.platform == "win32":
        pytest.skip("File locking integration test requires fcntl (non-Windows only).")

    import errno
    import fcntl

    import kalshi_research.cli.alerts as alerts_cli

    log_path = tmp_path / "alert_monitor.log"
    monkeypatch.setattr(alerts_cli, "_ALERT_MONITOR_LOG_PATH", log_path)

    real_popen = subprocess.Popen
    spawned: list[subprocess.Popen] = []

    def _popen_stub(args: list[str], **kwargs: object) -> subprocess.Popen:
        del args
        proc = real_popen([sys.executable, "-c", "import time; time.sleep(60)"], **kwargs)
        spawned.append(proc)
        return proc

    monkeypatch.setattr(alerts_cli.subprocess, "Popen", _popen_stub)

    try:
        pid, _ = alerts_cli._spawn_alert_monitor_daemon(
            interval=60,
            once=False,
            max_pages=None,
            environment="demo",
            output_file=None,
            webhook_url=None,
        )
        assert spawned and pid == spawned[0].pid

        with pytest.raises(RuntimeError, match="already be running"):
            alerts_cli._spawn_alert_monitor_daemon(
                interval=60,
                once=False,
                max_pages=None,
                environment="demo",
                output_file=None,
                webhook_url=None,
            )

        lock_acquired = False
        for _ in range(10):
            try:
                with log_path.open("a") as log_file:
                    fcntl.flock(log_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                lock_acquired = True
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN):
                    raise
            time.sleep(0.05)

        assert lock_acquired is False, "Expected daemon lock to be held by child process"
    finally:
        for proc in spawned:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)

    with log_path.open("a") as log_file:
        fcntl.flock(log_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
