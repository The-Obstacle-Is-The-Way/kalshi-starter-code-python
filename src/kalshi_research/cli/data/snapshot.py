"""Price snapshot command."""

from pathlib import Path
from typing import Annotated

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

from kalshi_research.cli.utils import console, run_async
from kalshi_research.paths import DEFAULT_DB_PATH


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
    from kalshi_research.cli.db import open_db
    from kalshi_research.data import DataFetcher

    async def _snapshot() -> None:
        async with open_db(db_path) as db, DataFetcher(db) as fetcher:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Taking snapshot...", total=None)
                count = await fetcher.take_snapshot(status=status, max_pages=max_pages)

        console.print(f"[green]✓[/green] Took {count} price snapshots")

    run_async(_snapshot())
