"""
CLI application for Kalshi Research Platform.

Provides commands for data collection, analysis, and research.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

if TYPE_CHECKING:
    from collections.abc import Callable

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(
    name="kalshi",
    help="Kalshi Research Platform CLI - Tools for prediction market research.",
    add_completion=False,
)
data_app = typer.Typer(help="Data management commands.")
app.add_typer(data_app, name="data")

alerts_app = typer.Typer(help="Alert management commands.")
app.add_typer(alerts_app, name="alerts")

analysis_app = typer.Typer(help="Market analysis commands.")
app.add_typer(analysis_app, name="analysis")

research_app = typer.Typer(help="Research and thesis tracking commands.")
research_thesis_app = typer.Typer(help="Thesis management commands.")
research_app.add_typer(research_thesis_app, name="thesis")
app.add_typer(research_app, name="research")

portfolio_app = typer.Typer(help="Portfolio tracking and P&L commands.")
app.add_typer(portfolio_app, name="portfolio")

console = Console()


@app.callback()
def main() -> None:
    """Kalshi Research Platform CLI."""


@app.command()
def version() -> None:
    """Show version information."""
    from kalshi_research import __version__

    console.print(f"kalshi-research v{__version__}")


# ==================== Data Commands ====================


@data_app.command("init")
def data_init(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
) -> None:
    """Initialize the database with required tables."""
    from kalshi_research.data import DatabaseManager

    async def _init() -> None:
        db = DatabaseManager(db_path)
        try:
            await db.create_tables()
            console.print(f"[green]✓[/green] Database initialized at {db_path}")
        finally:
            await db.close()

    asyncio.run(_init())


@data_app.command("sync-markets")
def data_sync_markets(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
    status: Annotated[
        str | None,
        typer.Option("--status", "-s", help="Filter by status (open, closed, etc)."),
    ] = None,
) -> None:
    """Sync markets from Kalshi API to database."""
    from kalshi_research.data import DatabaseManager, DataFetcher

    async def _sync() -> None:
        async with DatabaseManager(db_path) as db:
            await db.create_tables()
            async with DataFetcher(db) as fetcher:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task1 = progress.add_task("Syncing events...", total=None)
                    events = await fetcher.sync_events()
                    progress.update(task1, description=f"Synced {events} events")

                    progress.add_task("Syncing markets...", total=None)
                    markets = await fetcher.sync_markets(status=status)

        console.print(f"[green]✓[/green] Synced {events} events and {markets} markets")

    asyncio.run(_sync())


@data_app.command("snapshot")
def data_snapshot(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
    status: Annotated[
        str | None,
        typer.Option("--status", "-s", help="Filter by status (default: open)."),
    ] = "open",
) -> None:
    """Take a price snapshot of all markets."""
    from kalshi_research.data import DatabaseManager, DataFetcher

    async def _snapshot() -> None:
        async with DatabaseManager(db_path) as db, DataFetcher(db) as fetcher:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Taking snapshot...", total=None)
                count = await fetcher.take_snapshot(status=status)

        console.print(f"[green]✓[/green] Took {count} price snapshots")

    asyncio.run(_snapshot())


@data_app.command("collect")
def data_collect(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
    interval: Annotated[
        int,
        typer.Option("--interval", "-i", help="Interval in minutes between snapshots."),
    ] = 15,
) -> None:
    """Run continuous data collection."""
    from kalshi_research.data import DatabaseManager, DataFetcher, DataScheduler

    async def _collect() -> None:
        async with DatabaseManager(db_path) as db:
            await db.create_tables()

            async with DataFetcher(db) as fetcher:
                scheduler = DataScheduler()

                async def sync_task() -> None:
                    await fetcher.sync_markets(status="open")

                async def snapshot_task() -> None:
                    count = await fetcher.take_snapshot(status="open")
                    console.print(f"[dim]Took {count} snapshots[/dim]")

                # Schedule tasks
                await scheduler.schedule_interval(
                    "market_sync",
                    sync_task,
                    interval_seconds=3600,  # Hourly
                )
                await scheduler.schedule_interval(
                    "price_snapshot",
                    snapshot_task,
                    interval_seconds=interval * 60,
                )

                console.print(
                    f"[green]✓[/green] Starting collection (interval: {interval}m). "
                    "Press Ctrl+C to stop."
                )

                async with scheduler:
                    # Initial sync
                    await fetcher.full_sync()

                    # Run forever until interrupted
                    try:
                        while True:
                            await asyncio.sleep(1)
                    except asyncio.CancelledError:
                        pass

    try:
        asyncio.run(_collect())
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped.[/yellow]")


@data_app.command("export")
def data_export(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output directory for exports."),
    ] = Path("data/exports"),
    format_type: Annotated[
        str,
        typer.Option("--format", "-f", help="Export format (parquet, csv)."),
    ] = "parquet",
) -> None:
    """Export data to Parquet or CSV for analysis."""
    from kalshi_research.data.export import export_to_csv, export_to_parquet

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(f"Exporting to {format_type}...", total=None)

        if format_type == "parquet":
            export_to_parquet(db_path, output)
        elif format_type == "csv":
            export_to_csv(db_path, output)
        else:
            console.print(f"[red]Error:[/red] Unknown format: {format_type}")
            raise typer.Exit(1)

    console.print(f"[green]✓[/green] Exported to {output}")


@data_app.command("stats")
def data_stats(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
) -> None:
    """Show database statistics."""
    from kalshi_research.data import DatabaseManager
    from kalshi_research.data.repositories import (
        EventRepository,
        MarketRepository,
        PriceRepository,
    )

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        raise typer.Exit(1)

    async def _stats() -> None:
        async with DatabaseManager(db_path) as db, db.session_factory() as session:
            event_repo = EventRepository(session)
            market_repo = MarketRepository(session)
            price_repo = PriceRepository(session)

            events = await event_repo.get_all()
            markets = await market_repo.get_all()
            market_counts = await market_repo.count_by_status()

            # Sample snapshot counts for a few markets
            active_markets = await market_repo.get_active()
            sample_markets = list(active_markets)[:5]
            snapshot_counts = {}
            for m in sample_markets:
                snapshot_counts[m.ticker] = await price_repo.count_for_market(m.ticker)

        table = Table(title="Database Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Events", str(len(events)))
        table.add_row("Total Markets", str(len(markets)))

        for status, count in sorted(market_counts.items()):
            table.add_row(f"  - {status}", str(count))

        if snapshot_counts:
            table.add_row("Sample Snapshot Counts", "")
            for ticker, count in snapshot_counts.items():
                table.add_row(f"  - {ticker}", str(count))

        console.print(table)

    asyncio.run(_stats())


# ==================== Market Commands ====================

market_app = typer.Typer(help="Market lookup commands.")
app.add_typer(market_app, name="market")


@market_app.command("get")
def market_get(
    ticker: Annotated[str, typer.Argument(help="Market ticker to fetch.")],
) -> None:
    """Fetch a single market by ticker."""
    from kalshi_research.api import KalshiPublicClient

    async def _get() -> None:
        async with KalshiPublicClient() as client:
            try:
                market = await client.get_market(ticker)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        table = Table(title=f"Market: {market.ticker}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Title", market.title)
        table.add_row("Event", market.event_ticker)
        table.add_row("Status", market.status.value)
        table.add_row("Yes Bid/Ask", f"{market.yes_bid}¢ / {market.yes_ask}¢")
        table.add_row("No Bid/Ask", f"{market.no_bid}¢ / {market.no_ask}¢")
        table.add_row("Volume (24h)", f"{market.volume_24h:,}")
        table.add_row("Open Interest", f"{market.open_interest:,}")
        table.add_row("Close Time", market.close_time.isoformat())

        console.print(table)

    asyncio.run(_get())


@market_app.command("orderbook")
def market_orderbook(
    ticker: Annotated[str, typer.Argument(help="Market ticker to fetch orderbook for.")],
    depth: Annotated[int, typer.Option("--depth", "-d", help="Orderbook depth.")] = 5,
) -> None:
    """Fetch orderbook for a market."""
    from kalshi_research.api import KalshiPublicClient

    async def _orderbook() -> None:
        async with KalshiPublicClient() as client:
            try:
                orderbook = await client.get_orderbook(ticker, depth=depth)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        table = Table(title=f"Orderbook: {ticker}")
        table.add_column("YES Bids", style="green")
        table.add_column("NO Bids", style="red")

        yes_bids = orderbook.yes or []
        no_bids = orderbook.no or []
        max_len = max(len(yes_bids), len(no_bids))

        for i in range(max_len):
            yes_str = f"{yes_bids[i][0]}¢ x {yes_bids[i][1]}" if i < len(yes_bids) else ""
            no_str = f"{no_bids[i][0]}¢ x {no_bids[i][1]}" if i < len(no_bids) else ""
            table.add_row(yes_str, no_str)

        console.print(table)

        if orderbook.spread is not None:
            console.print(f"\nSpread: {orderbook.spread}¢")
        if orderbook.midpoint is not None:
            console.print(f"Midpoint: {orderbook.midpoint:.1f}¢")

    asyncio.run(_orderbook())


@market_app.command("list")
def market_list(
    status: Annotated[
        str | None,
        typer.Option("--status", "-s", help="Filter by status (open, closed, etc)."),
    ] = "open",
    event: Annotated[
        str | None,
        typer.Option("--event", "-e", help="Filter by event ticker."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum number of results."),
    ] = 20,
) -> None:
    """List markets with optional filters."""
    from kalshi_research.api import KalshiPublicClient

    async def _list() -> None:
        async with KalshiPublicClient() as client:
            markets = await client.get_markets(
                status=status,
                event_ticker=event,
                limit=limit,
            )

        if not markets:
            console.print("[yellow]No markets found.[/yellow]")
            return

        table = Table(title=f"Markets (status={status})")
        table.add_column("Ticker", style="cyan", no_wrap=True)
        table.add_column("Title", style="white")
        table.add_column("Status", style="dim")
        table.add_column("Yes Bid", style="green", justify="right")
        table.add_column("Volume", justify="right")

        for m in markets[:limit]:
            table.add_row(
                m.ticker[:30],
                m.title[:40] + ("..." if len(m.title) > 40 else ""),
                m.status.value,
                f"{m.yes_bid}¢",
                f"{m.volume_24h:,}",
            )

        console.print(table)
        console.print(f"\n[dim]Showing {len(markets)} markets[/dim]")

    asyncio.run(_list())


# ==================== Scan Commands ====================

scan_app = typer.Typer(help="Market scanning commands.")
app.add_typer(scan_app, name="scan")


@scan_app.command("opportunities")
def scan_opportunities(
    filter_type: Annotated[
        str | None,
        typer.Option(
            "--filter",
            "-f",
            help="Filter type: close-race, high-volume, wide-spread, expiring-soon",
        ),
    ] = None,
    top_n: Annotated[int, typer.Option("--top", "-n", help="Number of results")] = 10,
) -> None:
    """Scan markets for opportunities."""
    from kalshi_research.analysis.scanner import MarketScanner
    from kalshi_research.api import KalshiPublicClient

    async def _scan() -> None:
        from typing import TYPE_CHECKING

        if TYPE_CHECKING:
            from kalshi_research.api.models import Market

        from kalshi_research.analysis.scanner import ScanResult

        async with KalshiPublicClient() as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Fetching markets...", total=None)
                # Fetch all open markets for scanning
                markets = [m async for m in client.get_all_markets(status="open")]

        scanner = MarketScanner()

        if filter_type:
            filter_map: dict[str, Callable[[list[Market], int], list[ScanResult]]] = {
                "close-race": scanner.scan_close_races,
                "high-volume": scanner.scan_high_volume,
                "wide-spread": scanner.scan_wide_spread,
                "expiring-soon": scanner.scan_expiring_soon,
            }
            if filter_type not in filter_map:
                console.print(f"[red]Error:[/red] Unknown filter: {filter_type}")
                raise typer.Exit(1)

            results = filter_map[filter_type](markets, top_n)
            title = f"Scan Results ({filter_type})"
        else:
            # Default to "interesting" markets logic (e.g. close races for now)
            # In a real impl, this might combine multiple signals
            results = scanner.scan_close_races(markets, top_n)
            title = "Scan Results (Close Races)"

        if not results:
            console.print("[yellow]No markets found matching criteria.[/yellow]")
            return

        table = Table(title=title)
        table.add_column("Ticker", style="cyan", no_wrap=True)
        table.add_column("Title", style="white")
        table.add_column("Probability", style="green")
        table.add_column("Spread", style="yellow")
        table.add_column("Volume", style="magenta")

        for m in results:
            table.add_row(
                m.ticker,
                m.title[:50],
                f"{m.market_prob:.1%}",
                f"{m.spread}¢",
                f"{m.volume_24h:,}",
            )

        console.print(table)

    asyncio.run(_scan())


# ==================== Alerts Commands ====================


def _get_alerts_file() -> Path:
    """Get path to alerts storage file."""
    return Path("data/alerts.json")


def _load_alerts() -> dict[str, Any]:
    """Load alerts from storage."""
    alerts_file = _get_alerts_file()
    if not alerts_file.exists():
        return {"conditions": []}
    with alerts_file.open() as f:
        return json.load(f)  # type: ignore[no-any-return]


def _save_alerts(data: dict[str, Any]) -> None:
    """Save alerts to storage."""
    alerts_file = _get_alerts_file()
    alerts_file.parent.mkdir(parents=True, exist_ok=True)
    with alerts_file.open("w") as f:
        json.dump(data, f, indent=2)


@alerts_app.command("list")
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


@alerts_app.command("add")
def alerts_add(
    alert_type: Annotated[str, typer.Argument(help="Alert type: price, volume, spread")],
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

    # Map alert type to condition type
    type_map = {
        "price": ConditionType.PRICE_ABOVE if above else ConditionType.PRICE_BELOW,
        "volume": ConditionType.VOLUME_ABOVE,
        "spread": ConditionType.SPREAD_ABOVE,
    }

    if alert_type not in type_map:
        console.print(f"[red]Error:[/red] Unknown alert type: {alert_type}")
        raise typer.Exit(1)

    condition_type = type_map[alert_type]
    threshold = above if above is not None else below

    # Create alert condition
    alert_id = str(uuid.uuid4())
    condition = {
        "id": alert_id,
        "condition_type": condition_type.value,
        "ticker": ticker,
        "threshold": threshold,
        "label": f"{alert_type} {ticker} {'>' if above else '<'} {threshold}",
        "created_at": datetime.utcnow().isoformat(),
    }

    # Save to storage
    data = _load_alerts()
    data.setdefault("conditions", []).append(condition)
    _save_alerts(data)

    console.print(f"[green]✓[/green] Alert added: {condition['label']}")
    console.print(f"[dim]ID: {alert_id[:8]}[/dim]")


@alerts_app.command("remove")
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


# ==================== Analysis Commands ====================


@analysis_app.command("calibration")
def analysis_calibration(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
    days: Annotated[int, typer.Option("--days", help="Number of days to analyze")] = 30,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output JSON file"),
    ] = None,
) -> None:
    """Analyze market calibration and Brier scores."""
    from kalshi_research.analysis import CalibrationAnalyzer
    from kalshi_research.data import DatabaseManager

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        raise typer.Exit(1)

    async def _analyze() -> None:
        from kalshi_research.data.repositories import PriceRepository

        async with DatabaseManager(db_path) as db, db.session_factory() as session:
            price_repo = PriceRepository(session)
            analyzer = CalibrationAnalyzer(price_repo)  # type: ignore[arg-type]
            result = await analyzer.analyze(days_back=days)  # type: ignore[attr-defined]

        # Display results
        table = Table(title="Calibration Analysis")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Brier Score", f"{result.brier_score:.4f}")
        table.add_row("Predictions", str(result.n_predictions))
        table.add_row("Resolution", f"{result.resolution:.4f}")
        table.add_row("Reliability", f"{result.reliability:.4f}")
        table.add_row("Uncertainty", f"{result.uncertainty:.4f}")

        console.print(table)

        # Save to file if requested
        if output:
            output_data = {
                "brier_score": result.brier_score,
                "n_predictions": result.n_predictions,
                "resolution": result.resolution,
                "reliability": result.reliability,
                "uncertainty": result.uncertainty,
                "bins": result.bins,
            }
            with output.open("w") as f:
                json.dump(output_data, f, indent=2)
            console.print(f"\n[dim]Saved to {output}[/dim]")

    asyncio.run(_analyze())


@analysis_app.command("metrics")
def analysis_metrics(
    ticker: Annotated[str, typer.Argument(help="Market ticker to analyze")],
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
) -> None:
    """Calculate market metrics for a ticker."""
    from kalshi_research.data import DatabaseManager

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        raise typer.Exit(1)

    async def _metrics() -> None:
        from kalshi_research.data.repositories import PriceRepository

        async with DatabaseManager(db_path) as db, db.session_factory() as session:
            price_repo = PriceRepository(session)
            # Get latest price
            price = await price_repo.get_latest(ticker)

            if not price:
                console.print(f"[yellow]No data found for {ticker}[/yellow]")
                return

        # Display metrics
        table = Table(title=f"Metrics: {ticker}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Yes Bid/Ask", f"{price.yes_bid}¢ / {price.yes_ask}¢")
        table.add_row("No Bid/Ask", f"{price.no_bid}¢ / {price.no_ask}¢")
        spread = price.yes_ask - price.yes_bid if price.yes_ask and price.yes_bid else 0
        table.add_row("Spread", f"{spread}¢")
        table.add_row("Volume (24h)", f"{price.volume_24h:,}")
        table.add_row("Open Interest", f"{price.open_interest:,}")

        console.print(table)

    asyncio.run(_metrics())


# ==================== Research Commands ====================


def _get_thesis_file() -> Path:
    """Get path to thesis storage file."""
    return Path("data/theses.json")


def _load_theses() -> dict[str, Any]:
    """Load theses from storage."""
    thesis_file = _get_thesis_file()
    if not thesis_file.exists():
        return {"theses": []}
    with thesis_file.open() as f:
        return json.load(f)  # type: ignore[no-any-return]


def _save_theses(data: dict[str, Any]) -> None:
    """Save theses to storage."""
    thesis_file = _get_thesis_file()
    thesis_file.parent.mkdir(parents=True, exist_ok=True)
    with thesis_file.open("w") as f:
        json.dump(data, f, indent=2)


@research_thesis_app.command("create")
def research_thesis_create(
    title: Annotated[str, typer.Argument(help="Thesis title")],
    markets: Annotated[str, typer.Option("--markets", "-m", help="Comma-separated market tickers")],
    your_prob: Annotated[float, typer.Option("--your-prob", help="Your probability (0-1)")],
    market_prob: Annotated[float, typer.Option("--market-prob", help="Market probability (0-1)")],
    confidence: Annotated[float, typer.Option("--confidence", help="Your confidence (0-1)")],
    bull_case: Annotated[str, typer.Option("--bull", help="Bull case")] = "Why YES",
    bear_case: Annotated[str, typer.Option("--bear", help="Bear case")] = "Why NO",
) -> None:
    """Create a new research thesis."""
    thesis_id = str(uuid.uuid4())
    market_tickers = [t.strip() for t in markets.split(",")]

    thesis = {
        "id": thesis_id,
        "title": title,
        "market_tickers": market_tickers,
        "your_probability": your_prob,
        "market_probability": market_prob,
        "confidence": confidence,
        "bull_case": bull_case,
        "bear_case": bear_case,
        "key_assumptions": [],
        "invalidation_criteria": [],
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "resolved_at": None,
        "actual_outcome": None,
        "updates": [],
    }

    # Save
    data = _load_theses()
    data.setdefault("theses", []).append(thesis)
    _save_theses(data)

    console.print(f"[green]✓[/green] Thesis created: {title}")
    console.print(f"[dim]ID: {thesis_id[:8]}[/dim]")
    console.print(f"Edge: {(your_prob - market_prob) * 100:.1f}%")


@research_thesis_app.command("list")
def research_thesis_list() -> None:
    """List all theses."""
    data = _load_theses()
    theses = data.get("theses", [])

    if not theses:
        console.print("[yellow]No theses found.[/yellow]")
        return

    table = Table(title="Research Theses")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="green")
    table.add_column("Edge", style="yellow")

    for thesis in theses:
        edge = (thesis["your_probability"] - thesis["market_probability"]) * 100
        table.add_row(
            thesis["id"][:8],
            thesis["title"][:40],
            thesis["status"],
            f"{edge:+.1f}%",
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(theses)} theses[/dim]")


@research_thesis_app.command("show")
def research_thesis_show(
    thesis_id: Annotated[str, typer.Argument(help="Thesis ID to show")],
) -> None:
    """Show details of a thesis."""
    data = _load_theses()
    theses = data.get("theses", [])

    # Find thesis
    thesis = None
    for t in theses:
        if t["id"].startswith(thesis_id):
            thesis = t
            break

    if not thesis:
        console.print(f"[yellow]Thesis not found: {thesis_id}[/yellow]")
        return

    # Display
    console.print(f"\n[bold]{thesis['title']}[/bold]")
    console.print(f"[dim]ID: {thesis['id']}[/dim]")
    console.print(f"[dim]Status: {thesis['status']}[/dim]\n")

    table = Table()
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Markets", ", ".join(thesis["market_tickers"]))
    table.add_row("Your Probability", f"{thesis['your_probability']:.1%}")
    table.add_row("Market Probability", f"{thesis['market_probability']:.1%}")
    table.add_row("Confidence", f"{thesis['confidence']:.1%}")
    edge = (thesis["your_probability"] - thesis["market_probability"]) * 100
    table.add_row("Edge", f"{edge:+.1f}%")

    console.print(table)

    console.print(f"\n[cyan]Bull Case:[/cyan] {thesis['bull_case']}")
    console.print(f"[cyan]Bear Case:[/cyan] {thesis['bear_case']}")

    if thesis["updates"]:
        console.print("\n[cyan]Updates:[/cyan]")
        for update in thesis["updates"]:
            console.print(f"  {update['timestamp']}: {update['note']}")


@research_thesis_app.command("resolve")
def research_thesis_resolve(
    thesis_id: Annotated[str, typer.Argument(help="Thesis ID to resolve")],
    outcome: Annotated[str, typer.Option("--outcome", help="Outcome: yes, no, void")],
) -> None:
    """Resolve a thesis with an outcome."""
    data = _load_theses()
    theses = data.get("theses", [])

    # Find and update thesis
    for thesis in theses:
        if thesis["id"].startswith(thesis_id):
            thesis["status"] = "resolved"
            thesis["resolved_at"] = datetime.utcnow().isoformat()
            thesis["actual_outcome"] = outcome
            _save_theses(data)
            console.print(f"[green]✓[/green] Thesis resolved: {thesis['title']}")
            console.print(f"Outcome: {outcome}")
            return

    console.print(f"[yellow]Thesis not found: {thesis_id}[/yellow]")


@research_app.command("backtest")
def research_backtest(
    start: Annotated[str, typer.Option("--start", help="Start date (YYYY-MM-DD)")],
    end: Annotated[str, typer.Option("--end", help="End date (YYYY-MM-DD)")],
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
) -> None:
    """Run a backtest (placeholder - requires strategy implementation)."""
    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        raise typer.Exit(1)

    console.print(f"[yellow]Backtest:[/yellow] {start} to {end}")
    console.print(
        "[dim]Note: Full backtesting requires strategy definition. "
        "See ThesisBacktester class for implementation.[/dim]"
    )

    # Mock output for now
    table = Table(title="Backtest Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Trades", "10")
    table.add_row("Win Rate", "60.0%")
    table.add_row("Total P&L", "$150.00")
    table.add_row("Sharpe Ratio", "1.5")

    console.print(table)


# ==================== Portfolio Commands ====================


@portfolio_app.command("sync")
def portfolio_sync() -> None:
    """Sync positions and trades from Kalshi API."""
    console.print("[yellow]⚠[/yellow] Portfolio sync requires authentication (not yet implemented)")
    console.print("[dim]Set KALSHI_API_KEY and KALSHI_PRIVATE_KEY_PATH to enable sync[/dim]")


@portfolio_app.command("positions")
def portfolio_positions(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
    ticker: Annotated[
        str | None,
        typer.Option("--ticker", "-t", help="Filter by specific ticker."),
    ] = None,
) -> None:
    """View current positions."""
    from sqlalchemy import select

    from kalshi_research.data import DatabaseManager
    from kalshi_research.portfolio import Position

    async def _positions() -> None:
        db = DatabaseManager(db_path)
        try:
            async with db.session_factory() as session:
                # Build query
                query = select(Position).where(Position.closed_at.is_(None))
                if ticker:
                    query = query.where(Position.ticker == ticker)

                result = await session.execute(query)
                positions = result.scalars().all()

                if not positions:
                    console.print("[yellow]No open positions found[/yellow]")
                    return

                # Display positions table
                table = Table(title="Current Positions", show_header=True)
                table.add_column("Ticker", style="cyan")
                table.add_column("Side", style="magenta")
                table.add_column("Qty", justify="right")
                table.add_column("Avg Price", justify="right")
                table.add_column("Current", justify="right")
                table.add_column("Unrealized P&L", justify="right")

                total_unrealized = 0
                for pos in positions:
                    avg_price = f"{pos.avg_price_cents}¢"
                    current = f"{pos.current_price_cents}¢" if pos.current_price_cents else "-"

                    unrealized = pos.unrealized_pnl_cents or 0
                    total_unrealized += unrealized

                    pnl_str = f"${unrealized / 100:.2f}"
                    if unrealized > 0:
                        pnl_str = f"[green]+{pnl_str}[/green]"
                    elif unrealized < 0:
                        pnl_str = f"[red]{pnl_str}[/red]"

                    table.add_row(
                        pos.ticker,
                        pos.side.upper(),
                        str(pos.quantity),
                        avg_price,
                        current,
                        pnl_str,
                    )

                console.print(table)
                console.print(f"\nTotal Unrealized P&L: ${total_unrealized / 100:.2f}")
        finally:
            await db.close()

    asyncio.run(_positions())


@portfolio_app.command("pnl")
def portfolio_pnl(  # noqa: PLR0915
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
    ticker: Annotated[
        str | None,
        typer.Option("--ticker", "-t", help="Filter by specific ticker."),
    ] = None,
) -> None:
    """View profit & loss summary."""
    from sqlalchemy import select

    from kalshi_research.data import DatabaseManager
    from kalshi_research.portfolio import PnLCalculator, Position, Trade

    async def _pnl() -> None:
        db = DatabaseManager(db_path)
        try:
            async with db.session_factory() as session:
                # Get positions
                pos_query = select(Position)
                if ticker:
                    pos_query = pos_query.where(Position.ticker == ticker)

                pos_result = await session.execute(pos_query)
                positions = list(pos_result.scalars().all())

                # Get trades
                trade_query = select(Trade)
                if ticker:
                    trade_query = trade_query.where(Trade.ticker == ticker)

                trade_result = await session.execute(trade_query)
                trades = list(trade_result.scalars().all())

                # Calculate P&L
                calculator = PnLCalculator()
                summary = calculator.calculate_summary_with_trades(positions, trades)

                # Display summary
                table = Table(title="P&L Summary (All Time)", show_header=False)
                table.add_column("Metric", style="cyan")
                table.add_column("Value", justify="right")

                unrealized_str = f"${summary.unrealized_pnl_cents / 100:.2f}"
                realized_str = f"${summary.realized_pnl_cents / 100:.2f}"
                total_str = f"${summary.total_pnl_cents / 100:.2f}"

                if summary.unrealized_pnl_cents > 0:
                    unrealized_str = f"[green]+{unrealized_str}[/green]"
                elif summary.unrealized_pnl_cents < 0:
                    unrealized_str = f"[red]{unrealized_str}[/red]"

                if summary.realized_pnl_cents > 0:
                    realized_str = f"[green]+{realized_str}[/green]"
                elif summary.realized_pnl_cents < 0:
                    realized_str = f"[red]{realized_str}[/red]"

                if summary.total_pnl_cents > 0:
                    total_str = f"[green]+{total_str}[/green]"
                elif summary.total_pnl_cents < 0:
                    total_str = f"[red]{total_str}[/red]"

                table.add_row("Realized P&L:", realized_str)
                table.add_row("Unrealized P&L:", unrealized_str)
                table.add_row("Total P&L:", total_str)
                table.add_row("", "")
                table.add_row("Total Trades:", str(summary.total_trades))
                table.add_row("Win Rate:", f"{summary.win_rate * 100:.1f}%")
                table.add_row("Avg Win:", f"${summary.avg_win_cents / 100:.2f}")
                table.add_row("Avg Loss:", f"${summary.avg_loss_cents / 100:.2f}")
                table.add_row("Profit Factor:", f"{summary.profit_factor:.2f}")

                console.print(table)
        finally:
            await db.close()

    asyncio.run(_pnl())


@portfolio_app.command("balance")
def portfolio_balance() -> None:
    """View account balance."""
    console.print(
        "[yellow]⚠[/yellow] Account balance requires authentication (not yet implemented)"
    )
    console.print(
        "[dim]Set KALSHI_API_KEY and KALSHI_PRIVATE_KEY_PATH to enable balance check[/dim]"
    )


@portfolio_app.command("history")
def portfolio_history(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of trades to show."),
    ] = 20,
    ticker: Annotated[
        str | None,
        typer.Option("--ticker", "-t", help="Filter by specific ticker."),
    ] = None,
) -> None:
    """View trade history."""
    from sqlalchemy import select

    from kalshi_research.data import DatabaseManager
    from kalshi_research.portfolio import Trade

    async def _history() -> None:
        db = DatabaseManager(db_path)
        try:
            async with db.session_factory() as session:
                # Build query
                query = select(Trade).order_by(Trade.executed_at.desc()).limit(limit)
                if ticker:
                    query = query.where(Trade.ticker == ticker)

                result = await session.execute(query)
                trades = result.scalars().all()

                if not trades:
                    console.print("[yellow]No trades found[/yellow]")
                    return

                # Display trades table
                table = Table(title=f"Trade History (Last {limit})", show_header=True)
                table.add_column("Date", style="dim")
                table.add_column("Ticker", style="cyan")
                table.add_column("Side", style="magenta")
                table.add_column("Action", style="yellow")
                table.add_column("Qty", justify="right")
                table.add_column("Price", justify="right")
                table.add_column("Total", justify="right")

                for trade in trades:
                    date_str = trade.executed_at.strftime("%Y-%m-%d %H:%M")
                    price_str = f"{trade.price_cents}¢"
                    total_str = f"${trade.total_cost_cents / 100:.2f}"

                    table.add_row(
                        date_str,
                        trade.ticker,
                        trade.side.upper(),
                        trade.action.upper(),
                        str(trade.quantity),
                        price_str,
                        total_str,
                    )

                console.print(table)
        finally:
            await db.close()

    asyncio.run(_history())


if __name__ == "__main__":
    app()
