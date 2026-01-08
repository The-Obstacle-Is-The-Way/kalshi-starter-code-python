"""
CLI application for Kalshi Research Platform.

Provides commands for data collection, analysis, and research.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from dotenv import find_dotenv, load_dotenv
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

_ALERT_MONITOR_LOG_PATH = Path("data/alert_monitor.log")


def _spawn_alert_monitor_daemon(
    *, interval: int, once: bool, max_pages: int | None, environment: str
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
    return proc.pid, _ALERT_MONITOR_LOG_PATH


@app.callback()
def main(
    environment: Annotated[
        str,
        typer.Option(
            "--env",
            "-e",
            help="API environment (prod/demo). Defaults to KALSHI_ENVIRONMENT or prod.",
        ),
    ] = "prod",
) -> None:
    """Kalshi Research Platform CLI."""
    import os

    from kalshi_research.api.config import Environment, set_environment

    load_dotenv(find_dotenv(usecwd=True))

    # Priority: CLI flag > KALSHI_ENVIRONMENT env var > default "prod"
    env_var = os.getenv("KALSHI_ENVIRONMENT")

    # If user didn't override --env (still "prod") and env var is set, use env var
    final_env = environment
    if environment == "prod" and env_var:
        final_env = env_var

    try:
        set_environment(Environment(final_env))
    except ValueError:
        console.print(
            f"[yellow]Warning:[/yellow] Invalid environment '{final_env}', defaulting to prod"
        )
        set_environment(Environment.PRODUCTION)


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
    max_pages: Annotated[
        int | None,
        typer.Option(
            "--max-pages",
            help="Optional pagination safety limit. None = iterate until exhausted.",
        ),
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
                    events = await fetcher.sync_events(max_pages=max_pages)
                    progress.update(task1, description=f"Synced {events} events")

                    progress.add_task("Syncing markets...", total=None)
                    markets = await fetcher.sync_markets(status=status, max_pages=max_pages)

        console.print(f"[green]✓[/green] Synced {events} events and {markets} markets")

    asyncio.run(_sync())


@data_app.command("sync-settlements")
def data_sync_settlements(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
    max_pages: Annotated[
        int | None,
        typer.Option(
            "--max-pages",
            help="Optional pagination safety limit. None = iterate until exhausted.",
        ),
    ] = None,
) -> None:
    """Sync settled market outcomes from Kalshi API to database.

    Notes:
        The public markets endpoint provides a `result` but does not expose a clear settlement
        timestamp.
        We store `Settlement.settled_at` using `Market.expiration_time` as a documented proxy.
    """
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
                    progress.add_task("Syncing settlements...", total=None)
                    settlements = await fetcher.sync_settlements(max_pages=max_pages)

        console.print(f"[green]✓[/green] Synced {settlements} settlements")

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
    max_pages: Annotated[
        int | None,
        typer.Option(
            "--max-pages",
            help="Optional pagination safety limit. None = iterate until exhausted.",
        ),
    ] = None,
) -> None:
    """Take a price snapshot of all markets."""
    from kalshi_research.data import DatabaseManager, DataFetcher

    async def _snapshot() -> None:
        async with DatabaseManager(db_path) as db:
            await db.create_tables()

            async with DataFetcher(db) as fetcher:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    progress.add_task("Taking snapshot...", total=None)
                    count = await fetcher.take_snapshot(status=status, max_pages=max_pages)

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
    once: Annotated[
        bool,
        typer.Option("--once", help="Run a single full sync and exit."),
    ] = False,
    max_pages: Annotated[
        int | None,
        typer.Option(
            "--max-pages",
            help="Optional pagination safety limit. None = iterate until exhausted.",
        ),
    ] = None,
) -> None:
    """Run continuous data collection."""
    from kalshi_research.data import DatabaseManager, DataFetcher, DataScheduler

    async def _collect() -> None:
        async with DatabaseManager(db_path) as db:
            await db.create_tables()

            async with DataFetcher(db) as fetcher:
                if once:
                    counts = await fetcher.full_sync(max_pages=max_pages)
                    console.print(
                        "[green]✓[/green] Full sync complete: "
                        f"{counts['events']} events, {counts['markets']} markets, "
                        f"{counts['snapshots']} snapshots"
                    )
                    return

                scheduler = DataScheduler()

                async def sync_task() -> None:
                    await fetcher.sync_markets(status="open", max_pages=max_pages)

                async def snapshot_task() -> None:
                    count = await fetcher.take_snapshot(status="open", max_pages=max_pages)
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
                    await fetcher.full_sync(max_pages=max_pages)

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
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                market = await client.get_market(ticker)
            except KalshiAPIError as e:
                console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
                raise typer.Exit(1) from None
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
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                orderbook = await client.get_orderbook(ticker, depth=depth)
            except KalshiAPIError as e:
                console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
                raise typer.Exit(1) from None
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
    min_volume: Annotated[
        int,
        typer.Option(
            "--min-volume",
            help="Minimum 24h volume (close-race filter only).",
        ),
    ] = 0,
    max_spread: Annotated[
        int,
        typer.Option(
            "--max-spread",
            help="Maximum bid-ask spread in cents (close-race filter only).",
        ),
    ] = 100,
    max_pages: Annotated[
        int | None,
        typer.Option(
            "--max-pages",
            help="Optional pagination safety limit for market fetch (None = full).",
        ),
    ] = None,
) -> None:
    """Scan markets for opportunities."""
    from kalshi_research.analysis.scanner import MarketScanner
    from kalshi_research.api import KalshiPublicClient

    async def _scan() -> None:
        async with KalshiPublicClient() as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Fetching markets...", total=None)
                # Fetch all open markets for scanning
                markets = [
                    m async for m in client.get_all_markets(status="open", max_pages=max_pages)
                ]

        scanner = MarketScanner()

        if filter_type:
            if filter_type == "close-race":
                results = scanner.scan_close_races(
                    markets,
                    top_n,
                    min_volume_24h=min_volume,
                    max_spread=max_spread,
                )
                title = "Scan Results (close-race)"
            elif filter_type == "high-volume":
                results = scanner.scan_high_volume(markets, top_n)
                title = "Scan Results (high-volume)"
            elif filter_type == "wide-spread":
                results = scanner.scan_wide_spread(markets, top_n)
                title = "Scan Results (wide-spread)"
            elif filter_type == "expiring-soon":
                results = scanner.scan_expiring_soon(markets, top_n)
                title = "Scan Results (expiring-soon)"
            else:
                console.print(f"[red]Error:[/red] Unknown filter: {filter_type}")
                raise typer.Exit(1)
        else:
            # Default to "interesting" markets logic (e.g. close races for now)
            # In a real impl, this might combine multiple signals
            results = scanner.scan_close_races(
                markets,
                top_n,
                min_volume_24h=min_volume,
                max_spread=max_spread,
            )
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


@scan_app.command("arbitrage")
def scan_arbitrage(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
    divergence_threshold: Annotated[
        float, typer.Option("--threshold", help="Min divergence to flag (0-1)")
    ] = 0.10,
    top_n: Annotated[int, typer.Option("--top", "-n", help="Number of results")] = 10,
    tickers_limit: Annotated[
        int,
        typer.Option(
            "--tickers-limit",
            help="Limit historical correlation analysis to N tickers (0 = analyze all tickers).",
        ),
    ] = 50,
    max_pages: Annotated[
        int | None,
        typer.Option(
            "--max-pages",
            help="Optional pagination safety limit for market fetch (None = full).",
        ),
    ] = None,
) -> None:
    """Find arbitrage opportunities from correlated markets."""
    from kalshi_research.analysis.correlation import CorrelationAnalyzer
    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.data import DatabaseManager

    if not db_path.exists():
        console.print(
            "[yellow]Warning:[/yellow] Database not found, analyzing current markets only"
        )

    async def _load_correlated_pairs(markets: list[Any]) -> list[Any]:
        if not db_path.exists():
            return []

        from kalshi_research.data.repositories import PriceRepository

        async with DatabaseManager(db_path) as db, db.session_factory() as session:
            price_repo = PriceRepository(session)

            tickers = [m.ticker for m in markets]
            if tickers_limit > 0 and len(tickers) > tickers_limit:
                console.print(
                    "[yellow]Warning:[/yellow] Limiting correlation analysis to first "
                    f"{tickers_limit} tickers (out of {len(tickers)}). "
                    "Use --tickers-limit to adjust."
                )
                tickers = tickers[:tickers_limit]

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Analyzing correlations...", total=None)

                snapshots = {}
                for ticker in tickers:
                    snaps = await price_repo.get_for_market(ticker, limit=100)
                    if snaps and len(snaps) > 30:
                        snapshots[ticker] = list(snaps)

            if len(snapshots) < 2:
                return []

            analyzer = CorrelationAnalyzer(min_correlation=0.5)
            return await analyzer.find_correlated_markets(snapshots, top_n=50)

    async def _scan() -> None:
        # Fetch current markets
        async with KalshiPublicClient() as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Fetching markets...", total=None)
                markets = [
                    m async for m in client.get_all_markets(status="open", max_pages=max_pages)
                ]

        if not markets:
            console.print("[yellow]No open markets found[/yellow]")
            return

        correlated_pairs = await _load_correlated_pairs(markets)

        analyzer = CorrelationAnalyzer()

        # Find arbitrage opportunities
        opportunities = analyzer.find_arbitrage_opportunities(
            markets, correlated_pairs, divergence_threshold=divergence_threshold
        )

        # Combine with inverse pairs
        for m1, m2, deviation in analyzer.find_inverse_markets(
            markets, tolerance=divergence_threshold
        ):
            from kalshi_research.analysis.correlation import ArbitrageOpportunity

            opportunities.append(
                ArbitrageOpportunity(
                    tickers=[m1.ticker, m2.ticker],
                    opportunity_type="inverse_sum",
                    expected_relationship="Sum to ~100%",
                    actual_values={
                        m1.ticker: (m1.yes_bid + m1.yes_ask) / 2.0 / 100.0,
                        m2.ticker: (m2.yes_bid + m2.yes_ask) / 2.0 / 100.0,
                        "sum": (m1.yes_bid + m1.yes_ask) / 2.0 / 100.0
                        + (m2.yes_bid + m2.yes_ask) / 2.0 / 100.0,
                    },
                    divergence=abs(deviation),
                    confidence=0.95,
                )
            )

        if not opportunities:
            console.print("[yellow]No arbitrage opportunities found[/yellow]")
            return

        # Sort by divergence
        opportunities.sort(key=lambda o: o.divergence, reverse=True)
        opportunities = opportunities[:top_n]

        # Display results
        table = Table(title="Arbitrage Opportunities")
        table.add_column("Tickers", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Expected", style="dim")
        table.add_column("Divergence", style="red")
        table.add_column("Confidence", style="green")

        for opp in opportunities:
            tickers_str = ", ".join(opp.tickers[:2])
            table.add_row(
                tickers_str[:30],
                opp.opportunity_type,
                opp.expected_relationship[:40],
                f"{opp.divergence:.2%}",
                f"{opp.confidence:.2f}",
            )

        console.print(table)
        console.print(f"\n[dim]Found {len(opportunities)} opportunities[/dim]")

    asyncio.run(_scan())


@scan_app.command("movers")
def scan_movers(  # noqa: PLR0915
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
    period: Annotated[str, typer.Option("--period", "-p", help="Time period: 1h, 6h, 24h")] = "24h",
    top_n: Annotated[int, typer.Option("--top", "-n", help="Number of results")] = 10,
    max_pages: Annotated[
        int | None,
        typer.Option(
            "--max-pages",
            help="Optional pagination safety limit for market fetch (None = full).",
        ),
    ] = None,
) -> None:
    """Show biggest price movers over a time period."""
    from datetime import timedelta

    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.data import DatabaseManager

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        console.print("[dim]Price history data is required. Run 'kalshi data collect' first.[/dim]")
        raise typer.Exit(1)

    # Parse period
    period_map = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}
    if period not in period_map:
        console.print(f"[red]Error:[/red] Invalid period: {period}. Use 1h, 6h, 24h, or 7d")
        raise typer.Exit(1)

    hours_back = period_map[period]

    async def _scan() -> None:
        from datetime import UTC

        from kalshi_research.data.repositories import PriceRepository

        def _as_utc(dt: datetime) -> datetime:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)

        # Get current markets
        async with KalshiPublicClient() as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Fetching current markets...", total=None)
                markets = [
                    m async for m in client.get_all_markets(status="open", max_pages=max_pages)
                ]

        market_lookup = {m.ticker: m for m in markets}

        # Get historical prices
        movers: list[dict[str, Any]] = []
        async with DatabaseManager(db_path) as db, db.session_factory() as session:
            price_repo = PriceRepository(session)

            cutoff_time = datetime.now(UTC) - timedelta(hours=hours_back)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(f"Analyzing price movements ({period})...", total=None)

                for ticker, market in market_lookup.items():
                    # Get snapshots from the period
                    snapshots = await price_repo.get_for_market(ticker, limit=1000)

                    if not snapshots:
                        continue

                    # Filter to time range
                    recent_snaps = [s for s in snapshots if _as_utc(s.snapshot_time) >= cutoff_time]
                    if len(recent_snaps) < 2:
                        continue

                    # Calculate price change
                    oldest = recent_snaps[-1]  # Oldest in range
                    newest = recent_snaps[0]  # Most recent

                    old_prob = oldest.implied_probability
                    new_prob = newest.implied_probability
                    price_change = new_prob - old_prob

                    if abs(price_change) > 0.01:  # At least 1% move
                        movers.append(
                            {
                                "ticker": ticker,
                                "title": market.title,
                                "price_change": price_change,
                                "old_price": old_prob,
                                "new_price": new_prob,
                                "volume": market.volume,
                            }
                        )

        if not movers:
            console.print(f"[yellow]No significant price movements in the last {period}[/yellow]")
            return

        # Sort by absolute change
        movers.sort(key=lambda m: abs(m["price_change"]), reverse=True)
        movers = movers[:top_n]

        # Display results
        table = Table(title=f"Biggest Movers ({period})")
        table.add_column("Ticker", style="cyan", no_wrap=True)
        table.add_column("Title", style="white")
        table.add_column("Change", style="yellow")
        table.add_column("Old → New", style="dim")
        table.add_column("Volume", style="magenta")

        for m in movers:
            change_pct = m["price_change"]
            color = "green" if change_pct > 0 else "red"
            arrow = "↑" if change_pct > 0 else "↓"

            table.add_row(
                m["ticker"],
                m["title"][:40],
                f"[{color}]{arrow} {abs(change_pct):.1%}[/{color}]",
                f"{m['old_price']:.1%} → {m['new_price']:.1%}",
                f"{m['volume']:,}",
            )

        console.print(table)
        console.print(f"\n[dim]Showing top {len(movers)} movers[/dim]")

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
        "created_at": datetime.now(UTC).isoformat(),
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


@alerts_app.command("monitor")
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
    from kalshi_research.api import KalshiPublicClient

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
        except OSError as exc:
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

    async def _monitor_loop() -> None:
        """Main monitoring loop."""

        async with KalshiPublicClient() as client:
            try:
                while True:
                    # Fetch all open markets (with progress for long-running fetch)
                    console.print("[dim]Fetching markets...[/dim]", end="")
                    markets = [
                        m async for m in client.get_all_markets(status="open", max_pages=max_pages)
                    ]
                    console.print(f"[dim] ({len(markets)} markets)[/dim]")

                    # Check conditions
                    alerts = await monitor.check_conditions(markets)

                    if alerts:
                        console.print(
                            f"\n[green]✓[/green] {len(alerts)} alert(s) triggered at "
                            f"{datetime.now()}"
                        )

                    if once:
                        console.print("[green]✓[/green] Single check complete")
                        return

                    # Wait for next check
                    await asyncio.sleep(interval)
            except KeyboardInterrupt:
                console.print("\n[yellow]Monitoring stopped[/yellow]")

    asyncio.run(_monitor_loop())


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
        from datetime import UTC, timedelta

        from kalshi_research.data.repositories import PriceRepository

        async with DatabaseManager(db_path) as db, db.session_factory() as session:
            price_repo = PriceRepository(session)
            from kalshi_research.data.repositories import SettlementRepository

            settlement_repo = SettlementRepository(session)
            cutoff = datetime.now(UTC) - timedelta(days=days)
            settlements = await settlement_repo.get_settled_after(cutoff)

            forecasts: list[float] = []
            outcomes: list[int] = []
            for settlement in settlements:
                if settlement.result not in {"yes", "no"}:
                    continue

                snaps = await price_repo.get_for_market(
                    settlement.ticker,
                    end_time=settlement.settled_at,
                    limit=1,
                )
                if not snaps:
                    continue

                snapshot = snaps[0]
                forecasts.append(snapshot.midpoint / 100.0)
                outcomes.append(1 if settlement.result == "yes" else 0)

        if not forecasts:
            console.print("[yellow]No settled markets with price history found[/yellow]")
            return

        analyzer = CalibrationAnalyzer()
        result = analyzer.compute_calibration(forecasts, outcomes)

        # Display results
        table = Table(title="Calibration Analysis")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Brier Score", f"{result.brier_score:.4f}")
        table.add_row("Samples", str(result.n_samples))
        table.add_row("Skill Score", f"{result.brier_skill_score:.4f}")
        table.add_row("Resolution", f"{result.resolution:.4f}")
        table.add_row("Reliability", f"{result.reliability:.4f}")
        table.add_row("Uncertainty", f"{result.uncertainty:.4f}")

        console.print(table)

        # Save to file if requested
        if output:
            output_data = {
                "brier_score": result.brier_score,
                "brier_skill_score": result.brier_skill_score,
                "n_samples": result.n_samples,
                "resolution": result.resolution,
                "reliability": result.reliability,
                "uncertainty": result.uncertainty,
                "bins": result.bins.tolist(),
                "predicted_probs": result.predicted_probs.tolist(),
                "actual_freqs": result.actual_freqs.tolist(),
                "bin_counts": result.bin_counts.tolist(),
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

        price = None
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
        spread = price.yes_ask - price.yes_bid
        table.add_row("Spread", f"{spread}¢")
        table.add_row("Volume (24h)", f"{price.volume_24h:,}")
        table.add_row("Open Interest", f"{price.open_interest:,}")

        console.print(table)

    asyncio.run(_metrics())


@analysis_app.command("correlation")
def analysis_correlation(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
    event: Annotated[
        str | None,
        typer.Option("--event", "-e", help="Filter by event ticker"),
    ] = None,
    tickers: Annotated[
        str | None,
        typer.Option("--tickers", "-t", help="Comma-separated list of tickers to analyze"),
    ] = None,
    min_correlation: Annotated[
        float, typer.Option("--min", help="Minimum correlation threshold")
    ] = 0.5,
    top_n: Annotated[int, typer.Option("--top", "-n", help="Number of results")] = 10,
) -> None:
    """Analyze correlations between markets."""
    from kalshi_research.analysis.correlation import CorrelationAnalyzer
    from kalshi_research.data import DatabaseManager

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        raise typer.Exit(1)

    async def _analyze() -> None:
        from kalshi_research.data.repositories import PriceRepository

        async with DatabaseManager(db_path) as db, db.session_factory() as session:
            price_repo = PriceRepository(session)

            # Fetch price snapshots
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Fetching price snapshots...", total=None)

                # Get tickers to analyze
                if tickers:
                    ticker_list = [t.strip() for t in tickers.split(",")]
                elif event:
                    # Get all markets for this event
                    from kalshi_research.data.repositories import MarketRepository

                    market_repo = MarketRepository(session)
                    event_markets = await market_repo.get_by_event(event)
                    ticker_list = [m.ticker for m in event_markets]
                else:
                    console.print("[yellow]Error:[/yellow] Must specify --event or --tickers")
                    raise typer.Exit(1)

                if len(ticker_list) < 2:
                    console.print(
                        "[yellow]Need at least 2 tickers to analyze correlations[/yellow]"
                    )
                    return

                # Fetch snapshots for each ticker
                snapshots = {}
                for ticker in ticker_list:
                    snaps = await price_repo.get_for_market(ticker, limit=1000)
                    if snaps:
                        snapshots[ticker] = list(snaps)

            if len(snapshots) < 2:
                console.print("[yellow]Not enough data to analyze correlations[/yellow]")
                return

            # Analyze correlations
            analyzer = CorrelationAnalyzer(min_correlation=min_correlation)
            results = await analyzer.find_correlated_markets(snapshots, top_n=top_n)

            if not results:
                console.print("[yellow]No significant correlations found[/yellow]")
                return

            # Display results
            table = Table(title="Market Correlations")
            table.add_column("Ticker A", style="cyan")
            table.add_column("Ticker B", style="cyan")
            table.add_column("Correlation", style="green")
            table.add_column("Type", style="yellow")
            table.add_column("Strength", style="magenta")
            table.add_column("Samples", style="dim")

            for result in results:
                table.add_row(
                    result.ticker_a,
                    result.ticker_b,
                    f"{result.pearson:.3f}",
                    result.correlation_type.value,
                    result.strength,
                    str(result.n_samples),
                )

            console.print(table)
            console.print(f"\n[dim]Found {len(results)} correlated pairs[/dim]")

    asyncio.run(_analyze())


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
        "created_at": datetime.now(UTC).isoformat(),
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
def research_thesis_show(  # noqa: PLR0915
    thesis_id: Annotated[str, typer.Argument(help="Thesis ID to show")],
    with_positions: Annotated[
        bool, typer.Option("--with-positions", help="Show linked positions")
    ] = False,
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
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

    # Show linked positions if requested
    if with_positions:
        from sqlalchemy import select

        from kalshi_research.data import DatabaseManager
        from kalshi_research.portfolio import Position

        async def _show_positions() -> None:
            db = DatabaseManager(db_path)
            try:
                async with db.session_factory() as session:
                    query = select(Position).where(Position.thesis_id == thesis["id"])
                    result = await session.execute(query)
                    positions = result.scalars().all()

                    if not positions:
                        console.print("\n[dim]No positions linked to this thesis.[/dim]")
                        return

                    # Display positions
                    console.print("\n[cyan]Linked Positions:[/cyan]")
                    pos_table = Table()
                    pos_table.add_column("Ticker", style="cyan")
                    pos_table.add_column("Side", style="magenta")
                    pos_table.add_column("Qty", justify="right")
                    pos_table.add_column("Avg Price", justify="right")
                    pos_table.add_column("P&L", justify="right")

                    for pos in positions:
                        pnl = pos.unrealized_pnl_cents or 0
                        pnl_str = f"${pnl / 100:.2f}"
                        if pnl > 0:
                            pnl_str = f"[green]+{pnl_str}[/green]"
                        elif pnl < 0:
                            pnl_str = f"[red]{pnl_str}[/red]"

                        pos_table.add_row(
                            pos.ticker,
                            pos.side.upper(),
                            str(pos.quantity),
                            f"{pos.avg_price_cents}¢",
                            pnl_str,
                        )

                    console.print(pos_table)
            finally:
                await db.close()

        asyncio.run(_show_positions())


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
            thesis["resolved_at"] = datetime.now(UTC).isoformat()
            thesis["actual_outcome"] = outcome
            _save_theses(data)
            console.print(f"[green]✓[/green] Thesis resolved: {thesis['title']}")
            console.print(f"Outcome: {outcome}")
            return

    console.print(f"[yellow]Thesis not found: {thesis_id}[/yellow]")


def _parse_backtest_dates(start: str, end: str) -> tuple[datetime, datetime]:
    """Parse and validate backtest dates."""
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError as e:
        console.print(f"[red]Error:[/red] Invalid date format: {e}")
        console.print("[dim]Use YYYY-MM-DD format.[/dim]")
        raise typer.Exit(1) from None

    if start_dt >= end_dt:
        console.print("[red]Error:[/red] Start date must be before end date")
        raise typer.Exit(1)

    return start_dt, end_dt


def _display_backtest_results(results: list[Any], start: str, end: str) -> None:
    """Helper to display backtest results."""
    # Calculate aggregate statistics
    total_trades = sum(r.total_trades for r in results)
    total_pnl = sum(r.total_pnl for r in results)
    total_wins = sum(r.winning_trades for r in results)
    avg_brier = sum(r.brier_score for r in results) / len(results) if results else 0

    # Display summary table
    summary_table = Table(title="Backtest Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Date Range", f"{start} to {end}")
    summary_table.add_row("Theses Tested", str(len(results)))
    summary_table.add_row("Total Trades", str(total_trades))
    summary_table.add_row(
        "Aggregate Win Rate",
        f"{total_wins / total_trades:.1%}" if total_trades > 0 else "N/A",
    )
    pnl_color = "green" if total_pnl >= 0 else "red"
    summary_table.add_row("Total P&L", f"[{pnl_color}]{total_pnl:+.0f}¢[/{pnl_color}]")
    summary_table.add_row("Avg Brier Score", f"{avg_brier:.4f}")

    console.print(summary_table)
    console.print()

    # Display per-thesis results
    detail_table = Table(title="Per-Thesis Results")
    detail_table.add_column("Thesis ID", style="cyan", max_width=15)
    detail_table.add_column("Trades", justify="right")
    detail_table.add_column("Win Rate", justify="right")
    detail_table.add_column("P&L", justify="right")
    detail_table.add_column("Brier", justify="right")
    detail_table.add_column("Sharpe", justify="right")

    for result in sorted(results, key=lambda r: r.total_pnl, reverse=True):
        pnl_str = f"{result.total_pnl:+.0f}¢"
        pnl_color = "green" if result.total_pnl >= 0 else "red"
        detail_table.add_row(
            result.thesis_id[:15],
            str(result.total_trades),
            f"{result.win_rate:.1%}" if result.total_trades > 0 else "N/A",
            f"[{pnl_color}]{pnl_str}[/{pnl_color}]",
            f"{result.brier_score:.4f}",
            f"{result.sharpe_ratio:.2f}" if result.sharpe_ratio != 0 else "N/A",
        )

    console.print(detail_table)


@research_app.command("backtest")
def research_backtest(
    start: Annotated[str, typer.Option("--start", help="Start date (YYYY-MM-DD)")],
    end: Annotated[str, typer.Option("--end", help="End date (YYYY-MM-DD)")],
    thesis_id: Annotated[
        str | None,
        typer.Option(
            "--thesis",
            "-t",
            help="Specific thesis ID to backtest (default: all resolved)",
        ),
    ] = None,
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
) -> None:
    """
    Run backtests on resolved theses using historical settlements.

    Uses the ThesisBacktester class to compute real P&L, win rate, and Brier scores
    from actual settlement data in the database.

    Examples:
        kalshi research backtest --start 2024-01-01 --end 2024-12-31
        kalshi research backtest --thesis abc123 --start 2024-06-01 --end 2024-12-31
    """
    from sqlalchemy import select

    from kalshi_research.data import DatabaseManager
    from kalshi_research.data.models import Settlement
    from kalshi_research.research.backtest import ThesisBacktester
    from kalshi_research.research.thesis import ThesisManager, ThesisStatus

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        console.print("[dim]Run 'kalshi data init' first.[/dim]")
        raise typer.Exit(1)

    async def _backtest() -> None:
        db = DatabaseManager(db_path)
        thesis_mgr = ThesisManager()
        backtester = ThesisBacktester()

        console.print(f"[dim]Backtesting from {start} to {end}...[/dim]")

        try:
            start_dt, end_dt = _parse_backtest_dates(start, end)

            # Load theses
            if thesis_id:
                thesis = thesis_mgr.get(thesis_id)
                if not thesis:
                    console.print(f"[red]Error:[/red] Thesis '{thesis_id}' not found")
                    console.print(
                        "[dim]Use 'kalshi research thesis list' to see available theses.[/dim]"
                    )
                    raise typer.Exit(1)
                theses = [thesis]
            else:
                theses = thesis_mgr.list_all()

            # Filter to resolved theses only
            resolved = [t for t in theses if t.status == ThesisStatus.RESOLVED]
            if not resolved:
                console.print("[yellow]No resolved theses to backtest[/yellow]")
                console.print(
                    "[dim]Theses must be resolved before backtesting. "
                    "Use 'kalshi research thesis resolve'.[/dim]"
                )
                return

            console.print(f"[dim]Found {len(resolved)} resolved theses[/dim]")

            # Load settlements from DB
            async with db.session_factory() as session:
                result = await session.execute(
                    select(Settlement).where(
                        Settlement.settled_at >= start_dt,
                        Settlement.settled_at <= end_dt,
                    )
                )
                settlements = list(result.scalars().all())

            if not settlements:
                console.print(f"[yellow]No settlements found between {start} and {end}[/yellow]")
                console.print(
                    "[dim]Run 'kalshi data sync-settlements' to fetch settlement data.[/dim]"
                )
                return

            console.print(f"[dim]Found {len(settlements)} settlements in date range[/dim]")

            # Run backtest with progress indicator
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(f"Backtesting {len(resolved)} theses...", total=None)
                results = await backtester.backtest_all(resolved, settlements)

            if not results:
                console.print("[yellow]No backtest results generated[/yellow]")
                console.print("[dim]This can happen if no theses match the settlement data.[/dim]")
                return

            _display_backtest_results(results, start, end)

        finally:
            await db.close()

    asyncio.run(_backtest())


# ==================== Portfolio Commands ====================


@portfolio_app.command("sync")
def portfolio_sync(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
    environment: Annotated[
        str | None,
        typer.Option("--env", help="Override global environment (demo or prod)."),
    ] = None,
    skip_mark_prices: Annotated[
        bool,
        typer.Option(
            "--skip-mark-prices",
            help="Skip fetching current market prices (faster sync).",
        ),
    ] = False,
) -> None:
    """Sync positions and trades from Kalshi API.

    Syncs positions, trades, cost basis (FIFO), mark prices, and unrealized P&L.
    """
    import os

    from kalshi_research.api import KalshiClient, KalshiPublicClient
    from kalshi_research.api.exceptions import KalshiAPIError
    from kalshi_research.data import DatabaseManager
    from kalshi_research.portfolio.syncer import PortfolioSyncer

    key_id = os.getenv("KALSHI_KEY_ID")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH")
    private_key_b64 = os.getenv("KALSHI_PRIVATE_KEY_B64")

    if not key_id or (not private_key_path and not private_key_b64):
        console.print("[red]Error:[/red] Portfolio sync requires authentication.")
        console.print(
            "[dim]Set KALSHI_KEY_ID and KALSHI_PRIVATE_KEY_PATH "
            "(or KALSHI_PRIVATE_KEY_B64) to enable portfolio sync[/dim]"
        )
        raise typer.Exit(1)

    async def _sync() -> None:
        db = DatabaseManager(db_path)
        try:
            await db.create_tables()
            async with KalshiClient(
                key_id=key_id,
                private_key_path=private_key_path,
                private_key_b64=private_key_b64,
                environment=environment,
            ) as client:
                syncer = PortfolioSyncer(client=client, db=db)

                # Sync trades first (needed for cost basis calculation)
                console.print("[dim]Syncing trades...[/dim]")
                trades_count = await syncer.sync_trades()
                console.print(f"[green]✓[/green] Synced {trades_count} trades")

                # Sync positions (computes cost basis from trades via FIFO)
                console.print("[dim]Syncing positions + cost basis (FIFO)...[/dim]")
                positions_count = await syncer.sync_positions()
                console.print(f"[green]✓[/green] Synced {positions_count} positions")

                # Update mark prices + unrealized P&L (requires public API)
                if not skip_mark_prices and positions_count > 0:
                    console.print("[dim]Fetching mark prices...[/dim]")
                    # Use same environment for public client
                    async with KalshiPublicClient(environment=environment) as public_client:
                        updated = await syncer.update_mark_prices(public_client)
                        console.print(
                            f"[green]✓[/green] Updated mark prices for {updated} positions"
                        )

                console.print(
                    f"\n[green]✓[/green] Portfolio sync complete: "
                    f"{positions_count} positions, {trades_count} trades"
                )

        except KalshiAPIError as e:
            console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
            raise typer.Exit(1) from None
        finally:
            await db.close()

    asyncio.run(_sync())


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
                    current = (
                        f"{pos.current_price_cents}¢"
                        if pos.current_price_cents is not None
                        else "-"
                    )

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
def portfolio_balance(
    environment: Annotated[
        str | None,
        typer.Option("--env", help="Override global environment (demo or prod)."),
    ] = None,
) -> None:
    """View account balance."""
    import os

    from kalshi_research.api import KalshiClient
    from kalshi_research.api.exceptions import KalshiAPIError

    key_id = os.getenv("KALSHI_KEY_ID")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH")
    private_key_b64 = os.getenv("KALSHI_PRIVATE_KEY_B64")

    if not key_id or (not private_key_path and not private_key_b64):
        console.print("[red]Error:[/red] Balance requires authentication.")
        console.print(
            "[dim]Set KALSHI_KEY_ID and KALSHI_PRIVATE_KEY_PATH "
            "(or KALSHI_PRIVATE_KEY_B64) to enable balance checks[/dim]"
        )
        raise typer.Exit(1)

    async def _balance() -> None:
        async with KalshiClient(
            key_id=key_id,
            private_key_path=private_key_path,
            private_key_b64=private_key_b64,
            environment=environment,
        ) as client:
            try:
                balance = await client.get_balance()
            except KalshiAPIError as e:
                console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
                raise typer.Exit(1) from None

        if not balance:
            console.print("[yellow]No balance data returned[/yellow]")
            return

        table = Table(title="Account Balance")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        for k, v in sorted(balance.items()):
            table.add_row(str(k), str(v))
        console.print(table)

    asyncio.run(_balance())


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


@portfolio_app.command("link")
def portfolio_link(
    ticker: Annotated[str, typer.Argument(help="Market ticker to link")],
    thesis: Annotated[str, typer.Option("--thesis", help="Thesis ID to link to")],
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
) -> None:
    """Link a position to a thesis."""
    from sqlalchemy import select

    from kalshi_research.data import DatabaseManager
    from kalshi_research.portfolio import Position

    async def _link() -> None:
        db = DatabaseManager(db_path)
        try:
            async with db.session_factory() as session:
                # Find open position
                query = select(Position).where(
                    Position.ticker == ticker, Position.closed_at.is_(None)
                )
                result = await session.execute(query)
                position = result.scalar_one_or_none()

                if not position:
                    console.print(f"[yellow]No open position found for {ticker}[/yellow]")
                    return

                # Update thesis_id
                position.thesis_id = thesis
                await session.commit()

                console.print(f"[green]✓[/green] Position {ticker} linked to thesis {thesis}")
        finally:
            await db.close()

    asyncio.run(_link())


@portfolio_app.command("suggest-links")
def portfolio_suggest_links(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
) -> None:
    """Suggest thesis-position links based on matching tickers."""
    from sqlalchemy import select

    from kalshi_research.data import DatabaseManager
    from kalshi_research.portfolio import Position

    async def _suggest() -> None:
        # Load theses
        data = _load_theses()
        theses = data.get("theses", [])

        if not theses:
            console.print("[yellow]No theses found.[/yellow]")
            return

        # Get unlinked positions
        db = DatabaseManager(db_path)
        try:
            async with db.session_factory() as session:
                query = select(Position).where(
                    Position.thesis_id.is_(None), Position.closed_at.is_(None)
                )
                result = await session.execute(query)
                positions = result.scalars().all()

                if not positions:
                    console.print("[yellow]No unlinked positions found.[/yellow]")
                    return

                # Find matches
                matches = []
                for pos in positions:
                    for thesis in theses:
                        if pos.ticker in thesis.get("market_tickers", []):
                            matches.append(
                                {
                                    "ticker": pos.ticker,
                                    "thesis_id": thesis["id"],
                                    "thesis_title": thesis["title"],
                                }
                            )

                if not matches:
                    console.print("[yellow]No matching thesis-position pairs found.[/yellow]")
                    return

                # Display suggestions
                table = Table(title="Suggested Thesis-Position Links")
                table.add_column("Ticker", style="cyan")
                table.add_column("Thesis ID", style="magenta")
                table.add_column("Thesis Title", style="white")

                for match in matches:
                    table.add_row(
                        match["ticker"],
                        match["thesis_id"][:8],
                        match["thesis_title"],
                    )

                console.print(table)
                console.print(
                    "\n[dim]To link: kalshi portfolio link TICKER --thesis THESIS_ID[/dim]"
                )
        finally:
            await db.close()

    asyncio.run(_suggest())


if __name__ == "__main__":
    app()
