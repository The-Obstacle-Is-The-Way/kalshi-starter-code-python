import asyncio
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.table import Table

from kalshi_research.cli.utils import (
    atomic_write_json,
    console,
    load_json_storage_file,
)
from kalshi_research.paths import DEFAULT_ALERT_LOG, DEFAULT_ALERTS_PATH

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
) -> tuple[int, Path]:
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

    daemon_env = dict(os.environ)
    daemon_env["KALSHI_ENVIRONMENT"] = environment
    daemon_env.setdefault("PYTHONUNBUFFERED", "1")

    _ALERT_MONITOR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _ALERT_MONITOR_LOG_PATH.open("a") as log_file:
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
    except Exception:
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
                    console.print(
                        f"\n[green]✓[/green] {len(alerts)} alert(s) triggered at {datetime.now()}"
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

    if above is None and below is None:
        console.print("[red]Error:[/red] Must specify either --above or --below")
        raise typer.Exit(1)

    # Validate: volume/spread/sentiment only support --above (no BELOW condition types exist)
    if alert_type in ("volume", "spread", "sentiment") and below is not None:
        console.print(f"[red]Error:[/red] {alert_type} alerts only support --above threshold")
        raise typer.Exit(1)

    # Map alert type to condition type
    type_map: dict[str, ConditionType] = {
        "price": ConditionType.PRICE_ABOVE if above else ConditionType.PRICE_BELOW,
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
    alert_id: Annotated[str, typer.Argument(help="Alert ID to remove")],
) -> None:
    """Remove an alert by ID."""
    data = _load_alerts()
    conditions = data.get("conditions", [])

    # Find and remove
    for i, cond in enumerate(conditions):
        if cond["id"].startswith(alert_id):
            removed = conditions.pop(i)
            _save_alerts(data)
            console.print(f"[green]✓[/green] Alert removed: {removed['label']}")
            return

    console.print(f"[yellow]Alert not found: {alert_id}[/yellow]")


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
) -> None:
    """Start monitoring alerts (runs in foreground)."""
    from kalshi_research.alerts import AlertMonitor
    from kalshi_research.alerts.conditions import AlertCondition, ConditionType
    from kalshi_research.alerts.notifiers import ConsoleNotifier

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
