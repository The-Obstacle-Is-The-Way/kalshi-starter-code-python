"""Monitor alerts command and related async helpers."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import structlog
import typer

from kalshi_research.cli.alerts._helpers import load_alerts, spawn_alert_monitor_daemon
from kalshi_research.cli.utils import console, run_async

if TYPE_CHECKING:
    from kalshi_research.alerts import AlertMonitor

logger = structlog.get_logger()


async def _compute_sentiment_shifts(
    tickers: set[str],
    *,
    db_path: Path,
) -> dict[str, float]:
    """Compute sentiment shifts for the given tickers.

    Args:
        tickers: Set of market tickers to compute sentiment shifts for.
        db_path: Path to the database file.

    Returns:
        Dictionary mapping ticker to sentiment shift value.
    """
    from kalshi_research.cli.db import open_db
    from kalshi_research.news import SentimentAggregator

    shifts: dict[str, float] = {}
    try:
        async with open_db(db_path) as db:
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
    """Monitor alerts by periodically fetching markets and evaluating conditions.

    Args:
        interval: Sleep interval (seconds) between checks (ignored when `once=True`).
        once: If true, run a single check and exit.
        max_pages: Maximum pages to fetch when listing open markets.
        monitor: Alert monitor containing configured conditions.
    """
    from kalshi_research.alerts.conditions import ConditionType
    from kalshi_research.cli.client_factory import public_client
    from kalshi_research.paths import DEFAULT_DB_PATH

    async with public_client() as client:
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
    data = load_alerts()
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
            pid, log_path = spawn_alert_monitor_daemon(
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
        # Parse expires_at if present (stored as ISO string or datetime)
        expires_at_raw = cond_data.get("expires_at")
        expires_at = (
            datetime.fromisoformat(expires_at_raw)
            if isinstance(expires_at_raw, str)
            else expires_at_raw
        )
        condition = AlertCondition(
            id=cond_data["id"],
            condition_type=ConditionType(cond_data["condition_type"]),
            ticker=cond_data["ticker"],
            threshold=cond_data["threshold"],
            label=cond_data.get("label", ""),
            expires_at=expires_at,
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

    run_async(
        _run_alert_monitor_loop(
            interval=interval,
            once=once,
            max_pages=max_pages,
            monitor=monitor,
        )
    )
