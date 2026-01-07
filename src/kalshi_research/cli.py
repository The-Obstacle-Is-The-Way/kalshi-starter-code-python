"""
CLI application for Kalshi Research Platform.

Provides commands for data collection, analysis, and research.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

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


if __name__ == "__main__":
    app()
