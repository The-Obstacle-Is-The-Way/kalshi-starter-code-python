"""Continuous data collection command."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from kalshi_research.cli.utils import console, run_async
from kalshi_research.paths import DEFAULT_DB_PATH


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
    include_mve_events: Annotated[
        bool,
        typer.Option(
            "--include-mve-events",
            help="Also sync multivariate events via /events/multivariate.",
        ),
    ] = False,
) -> None:
    """Run continuous data collection."""
    from kalshi_research.cli.db import open_db
    from kalshi_research.data import DataFetcher, DataScheduler

    async def _collect() -> None:
        async with open_db(db_path) as db, DataFetcher(db) as fetcher:
            if once:
                counts = await fetcher.full_sync(
                    max_pages=max_pages,
                    include_multivariate=include_mve_events,
                )
                console.print(
                    "[green]✓[/green] Full sync complete: "
                    f"{counts['events']} events, {counts['markets']} markets, "
                    f"{counts['snapshots']} snapshots"
                )
                return

            scheduler = DataScheduler()
            write_lock = asyncio.Lock()

            async def sync_task() -> None:
                async with write_lock:
                    await fetcher.sync_markets(status="open", max_pages=max_pages)

            async def snapshot_task() -> None:
                async with write_lock:
                    count = await fetcher.take_snapshot(status="open", max_pages=max_pages)
                    console.print(f"[dim]Took {count} snapshots[/dim]")

            # Schedule tasks
            await scheduler.schedule_interval(
                "market_sync",
                sync_task,
                interval_seconds=3600,  # Hourly
                run_immediately=False,
            )
            await scheduler.schedule_interval(
                "price_snapshot",
                snapshot_task,
                interval_seconds=interval * 60,
                run_immediately=False,
            )

            # Initial sync before starting scheduled tasks.
            # Prevents in-process overlap on startup.
            await fetcher.full_sync(
                max_pages=max_pages,
                include_multivariate=include_mve_events,
            )

            console.print(
                f"[green]✓[/green] Starting collection (interval: {interval}m). "
                "Press Ctrl+C to stop."
            )

            async with scheduler:
                # Run forever until interrupted
                try:
                    while True:
                        await asyncio.sleep(1)
                except asyncio.CancelledError:
                    pass

    run_async(_collect())
