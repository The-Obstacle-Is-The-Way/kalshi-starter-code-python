"""Database initialization command."""

from pathlib import Path
from typing import Annotated

import typer

from kalshi_research.cli.utils import console, run_async
from kalshi_research.paths import DEFAULT_DB_PATH


def data_init(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
) -> None:
    """Initialize the database with required tables."""
    from kalshi_research.cli.db import open_db

    async def _init() -> None:
        async with open_db(db_path):
            console.print(f"[green]✓[/green] Database initialized at {db_path}")

    run_async(_init())
