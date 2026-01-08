import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from kalshi_research.cli.utils import console
from kalshi_research.paths import DEFAULT_DB_PATH, DEFAULT_EXPORTS_DIR

app = typer.Typer(help="Data management commands.")


@app.command("init")
def data_init(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
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


@app.command("sync-markets")
def data_sync_markets(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
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


@app.command("sync-settlements")
def data_sync_settlements(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
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


@app.command("snapshot")
def data_snapshot(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
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


@app.command("collect")
def data_collect(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
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


@app.command("export")
def data_export(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output directory for exports."),
    ] = DEFAULT_EXPORTS_DIR,
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


@app.command("stats")
def data_stats(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
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
