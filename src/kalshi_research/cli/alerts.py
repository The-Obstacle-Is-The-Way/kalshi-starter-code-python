"""Typer CLI commands for creating and monitoring alerts."""

import asyncio
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import structlog
import typer
from rich.table import Table

from kalshi_research.cli.utils import (
    atomic_write_json,
    console,
    load_json_storage_file,
)
from kalshi_research.paths import DEFAULT_ALERT_LOG, DEFAULT_ALERTS_PATH

logger = structlog.get_logger()

app = typer.Typer(help="Alert management commands.")

_ALERT_MONITOR_LOG_PATH = DEFAULT_ALERT_LOG

if TYPE_CHECKING:
    from kalshi_research.alerts import AlertMonitor


def _get_alerts_file() -> Path:
    """Get path to alerts storage file."""
    return DEFAULT_ALERTS_PATH


def _load_alerts() -> dict[str, Any]:
    """Load alerts from storage."""
    alerts_file = _get_alerts_file()
    return load_json_storage_file(path=alerts_file, kind="Alerts", required_list_key="conditions")


def _save_alerts(data: dict[str, Any]) -> None:
    """Save alerts to storage."""
    alerts_file = _get_alerts_file()
    atomic_write_json(alerts_file, data)


def _spawn_alert_monitor_daemon(
    *,
    interval: int,
    once: bool,
    max_pages: int | None,
    environment: str,
    output_file: Path | None,
    webhook_url: str | None,
) -> tuple[int, Path]:
    import errno
    import os

    args = [
        sys.executable,
        "-m",
        "kalshi_research.cli",
        "alerts",
        "monitor",
        "--interval",
        str(interval),
    ]
    if max_pages is not None:
        args.extend(["--max-pages", str(max_pages)])
    if once:
        args.append("--once")
    if output_file is not None:
        args.extend(["--output-file", str(output_file)])
    if webhook_url is not None:
        args.extend(["--webhook-url", webhook_url])

    daemon_env = dict(os.environ)
    daemon_env["KALSHI_ENVIRONMENT"] = environment
    daemon_env.setdefault("PYTHONUNBUFFERED", "1")

    _ALERT_MONITOR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _ALERT_MONITOR_LOG_PATH.open("a") as log_file:
        if sys.platform != "win32":
            import fcntl

            try:
                fcntl.flock(log_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                if exc.errno in (errno.EACCES, errno.EAGAIN):
                    raise RuntimeError(
                        "Alert monitor daemon appears to already be running (log file is locked): "
                        f"{_ALERT_MONITOR_LOG_PATH}"
                    ) from None
                raise

        popen_kwargs: dict[str, Any] = {
            "stdin": subprocess.DEVNULL,
            "stdout": log_file,
            "stderr": log_file,
            "env": daemon_env,
        }
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = int(getattr(subprocess, "DETACHED_PROCESS", 0)) | int(
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            )
        else:
            popen_kwargs["start_new_session"] = True

        proc = subprocess.Popen(args, **popen_kwargs)

    # Quick sanity check: if the child dies immediately (import error, bad args),
    # don't claim the daemon started successfully.
    time.sleep(0.25)
    returncode = proc.poll()
    if isinstance(returncode, int) and (returncode != 0 or not once):
        raise RuntimeError(
            f"Daemon exited immediately with code {returncode}. See logs: {_ALERT_MONITOR_LOG_PATH}"
        )

    return proc.pid, _ALERT_MONITOR_LOG_PATH


async def _compute_sentiment_shifts(
    tickers: set[str],
    *,
    db_path: Path,
) -> dict[str, float]:
    from kalshi_research.data import DatabaseManager
    from kalshi_research.news import SentimentAggregator

    shifts: dict[str, float] = {}
    try:
        async with DatabaseManager(db_path) as db:
            aggregator = SentimentAggregator(db)
            for ticker in tickers:
                summary = await aggregator.get_market_summary(ticker, days=7, compare_previous=True)
                if summary and summary.score_change is not None:
                    shifts[ticker] = summary.score_change
    except Exception as e:
        logger.warning(
            "Failed to compute sentiment shifts; sentiment alerts will be skipped",
            error=str(e),
            exc_info=True,
        )
        return {}
    return shifts


async def _run_alert_monitor_loop(
    *,
    interval: int,
    once: bool,
    max_pages: int | None,
    monitor: "AlertMonitor",
) -> None:
    from kalshi_research.alerts.conditions import ConditionType
    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.paths import DEFAULT_DB_PATH

    async with KalshiPublicClient() as client:
        try:
            while True:
                console.print("[dim]Fetching markets...[/dim]", end="")
                markets = [
                    m async for m in client.get_all_markets(status="open", max_pages=max_pages)
                ]
                console.print(f"[dim] ({len(markets)} markets)[/dim]")

                sentiment_conditions = [
                    c
                    for c in monitor.list_conditions()
                    if c.condition_type == ConditionType.SENTIMENT_SHIFT
                ]
                sentiment_shift_by_ticker: dict[str, float] | None = None
                if sentiment_conditions:
                    sentiment_shift_by_ticker = await _compute_sentiment_shifts(
                        {c.ticker for c in sentiment_conditions},
                        db_path=DEFAULT_DB_PATH,
                    )

                alerts = await monitor.check_conditions(
                    markets,
                    sentiment_shift_by_ticker=sentiment_shift_by_ticker,
                )

                if alerts:
                    triggered_at = datetime.now(UTC)
                    console.print(
                        f"\n[green]✓[/green] {len(alerts)} alert(s) triggered at {triggered_at}"
                    )

                if once:
                    console.print("[green]✓[/green] Single check complete")
                    return

                await asyncio.sleep(interval)
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped[/yellow]")


@app.command("list")
def alerts_list() -> None:
    """List all active alerts."""

    data = _load_alerts()
    conditions = data.get("conditions", [])

    if not conditions:
        console.print("[yellow]No active alerts.[/yellow]")
        return

    table = Table(title="Active Alerts")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Ticker", style="white")
    table.add_column("Threshold", style="yellow")
    table.add_column("Label", style="dim")

    for cond in conditions:
        table.add_row(
            cond["id"][:8],
            cond["condition_type"],
            cond["ticker"],
            str(cond["threshold"]),
            cond.get("label", ""),
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(conditions)} alerts[/dim]")


@app.command("add")
def alerts_add(
    alert_type: Annotated[str, typer.Argument(help="Alert type: price, volume, spread, sentiment")],
    ticker: Annotated[str, typer.Argument(help="Market ticker to monitor")],
    above: Annotated[
        float | None, typer.Option("--above", help="Trigger when above threshold")
    ] = None,
    below: Annotated[
        float | None, typer.Option("--below", help="Trigger when below threshold")
    ] = None,
) -> None:
    """Add a new alert condition."""
    from kalshi_research.alerts import ConditionType

    alert_type = alert_type.strip().lower()

    if above is not None and below is not None:
        console.print("[red]Error:[/red] Specify only one of --above or --below")
        raise typer.Exit(1)

    if above is None and below is None:
        console.print("[red]Error:[/red] Must specify either --above or --below")
        raise typer.Exit(1)

    # Validate: volume/spread/sentiment only support --above (no BELOW condition types exist)
    if alert_type in ("volume", "spread", "sentiment") and below is not None:
        console.print(f"[red]Error:[/red] {alert_type} alerts only support --above threshold")
        raise typer.Exit(1)

    # Map alert type to condition type
    type_map: dict[str, ConditionType] = {
        "price": ConditionType.PRICE_ABOVE if above is not None else ConditionType.PRICE_BELOW,
        "volume": ConditionType.VOLUME_ABOVE,
        "spread": ConditionType.SPREAD_ABOVE,
        "sentiment": ConditionType.SENTIMENT_SHIFT,
    }

    if alert_type not in type_map:
        console.print(f"[red]Error:[/red] Unknown alert type: {alert_type}")
        raise typer.Exit(1)

    condition_type = type_map[alert_type]
    threshold = above if above is not None else below

    # Create alert condition
    alert_id = str(uuid.uuid4())
    comparison = ">" if above is not None else "<"
    if condition_type == ConditionType.SENTIMENT_SHIFT:
        comparison = "|Δ| ≥"
    condition = {
        "id": alert_id,
        "condition_type": condition_type.value,
        "ticker": ticker,
        "threshold": threshold,
        "label": f"{alert_type} {ticker} {comparison} {threshold}",
        "created_at": datetime.now(UTC).isoformat(),
    }

    # Save to storage
    data = _load_alerts()
    data.setdefault("conditions", []).append(condition)
    _save_alerts(data)

    console.print(f"[green]✓[/green] Alert added: {condition['label']}")
    console.print(f"[dim]ID: {alert_id[:8]}[/dim]")


@app.command("remove")
def alerts_remove(
    alert_id: Annotated[str, typer.Argument(help="Alert ID prefix to remove")],
) -> None:
    """Remove an alert by ID prefix."""
    data = _load_alerts()
    conditions = data.get("conditions", [])

    # Find and remove
    for i, cond in enumerate(conditions):
        if cond["id"].startswith(alert_id):
            removed = conditions.pop(i)
            _save_alerts(data)
            console.print(f"[green]✓[/green] Alert removed: {removed['label']}")
            return

    console.print(f"[red]Error:[/red] Alert not found: {alert_id}")
    raise typer.Exit(2)


@app.command("monitor")
def alerts_monitor(
    interval: Annotated[
        int, typer.Option("--interval", "-i", help="Check interval in seconds")
    ] = 60,
    daemon: Annotated[bool, typer.Option("--daemon", help="Run in background")] = False,
    once: Annotated[
        bool,
        typer.Option("--once", help="Run a single check cycle and exit."),
    ] = False,
    max_pages: Annotated[
        int | None,
        typer.Option(
            "--max-pages",
            help="Optional pagination safety limit for market fetch (None = full).",
        ),
    ] = None,
    output_file: Annotated[
        Path | None,
        typer.Option(
            "--output-file",
            help="Write triggered alerts to a JSONL file (one alert per line).",
        ),
    ] = None,
    webhook_url: Annotated[
        str | None,
        typer.Option(
            "--webhook-url",
            help="POST triggered alerts to a webhook URL (Slack/Discord style payload).",
        ),
    ] = None,
) -> None:
    """Start monitoring alerts (runs in foreground)."""
    from kalshi_research.alerts import AlertMonitor
    from kalshi_research.alerts.conditions import AlertCondition, ConditionType
    from kalshi_research.alerts.notifiers import ConsoleNotifier, FileNotifier, WebhookNotifier

    # Load alert conditions from storage
    data = _load_alerts()
    conditions_data = data.get("conditions", [])

    if not conditions_data:
        console.print(
            "[yellow]No alerts configured. Use 'kalshi alerts add' to create some.[/yellow]"
        )
        return

    if daemon:
        from kalshi_research.api.config import get_config

        environment_value = get_config().environment.value
        try:
            pid, log_path = _spawn_alert_monitor_daemon(
                interval=interval,
                once=once,
                max_pages=max_pages,
                environment=environment_value,
                output_file=output_file,
                webhook_url=webhook_url,
            )
        except (OSError, RuntimeError) as exc:
            console.print(f"[red]Error:[/red] Failed to start daemon: {exc}")
            raise typer.Exit(1) from None

        console.print(f"[green]✓[/green] Alert monitor started in background (PID: {pid})")
        console.print(f"[dim]Logs: {log_path}[/dim]")
        return

    # Create monitor and add notifier
    monitor = AlertMonitor()
    monitor.add_notifier(ConsoleNotifier())
    if output_file is not None:
        monitor.add_notifier(FileNotifier(output_file))
    if webhook_url is not None:
        monitor.add_notifier(WebhookNotifier(webhook_url))

    # Reconstruct AlertCondition objects from stored data
    for cond_data in conditions_data:
        condition = AlertCondition(
            id=cond_data["id"],
            condition_type=ConditionType(cond_data["condition_type"]),
            ticker=cond_data["ticker"],
            threshold=cond_data["threshold"],
            label=cond_data.get("label", ""),
        )
        monitor.add_condition(condition)

    if once:
        console.print(f"[green]✓[/green] Monitoring {len(conditions_data)} alerts (single check)")
        console.print("[dim]Running single check...[/dim]\n")
    else:
        console.print(
            f"[green]✓[/green] Monitoring {len(conditions_data)} alerts "
            f"(checking every {interval}s)"
        )
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    asyncio.run(
        _run_alert_monitor_loop(
            interval=interval,
            once=once,
            max_pages=max_pages,
            monitor=monitor,
        )
    )


@app.command("trim-log")
def alerts_trim_log(
    log_path: Annotated[
        Path,
        typer.Option("--log", help="Path to the alerts monitor log file."),
    ] = DEFAULT_ALERT_LOG,
    max_mb: Annotated[
        int,
        typer.Option("--max-mb", help="Trim the log when it exceeds this many MB."),
    ] = 50,
    keep_mb: Annotated[
        int,
        typer.Option("--keep-mb", help="When trimming, keep the last N MB."),
    ] = 5,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run/--apply",
            help="Preview changes without modifying the log (default: dry-run).",
        ),
    ] = True,
) -> None:
    """Trim the alerts monitor log to keep disk usage bounded."""
    import errno
    import os

    if max_mb <= 0:
        console.print("[red]Error:[/red] --max-mb must be > 0")
        raise typer.Exit(2)
    if keep_mb < 0:
        console.print("[red]Error:[/red] --keep-mb must be >= 0")
        raise typer.Exit(2)
    if keep_mb > max_mb:
        console.print("[red]Error:[/red] --keep-mb must be <= --max-mb")
        raise typer.Exit(2)

    if not log_path.exists():
        console.print(f"[yellow]No log file found at {log_path}[/yellow]")
        return

    size_bytes = log_path.stat().st_size
    max_bytes = max_mb * 1024 * 1024
    keep_bytes = keep_mb * 1024 * 1024

    if size_bytes <= max_bytes:
        console.print(f"[green]✓[/green] Log size OK ({size_bytes} bytes)")
        return

    if dry_run:
        console.print(
            f"[yellow]Dry-run:[/yellow] Would trim {log_path} "
            f"from {size_bytes} bytes to ~{keep_bytes} bytes"
        )
        return

    with log_path.open("r+b") as f:
        if sys.platform != "win32":
            import fcntl

            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                if exc.errno in (errno.EACCES, errno.EAGAIN):
                    console.print(
                        "[red]Error:[/red] Log file is locked. Stop the alert monitor daemon "
                        "before trimming."
                    )
                    raise typer.Exit(2) from None
                raise

        if keep_bytes <= 0:
            f.truncate(0)
        else:
            f.seek(0, os.SEEK_END)
            end_pos = f.tell()
            start_pos = max(0, end_pos - keep_bytes)
            f.seek(start_pos)
            tail = f.read()
            f.seek(0)
            f.truncate(0)
            f.write(tail)

    new_size = log_path.stat().st_size
    console.print(f"[green]✓[/green] Trimmed log to {new_size} bytes: {log_path}")
