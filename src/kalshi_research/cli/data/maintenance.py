"""Database maintenance commands (prune, vacuum)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from kalshi_research.cli.utils import console, run_async
from kalshi_research.paths import DEFAULT_DB_PATH


def data_prune(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    snapshots_older_than_days: Annotated[
        int | None,
        typer.Option(
            "--snapshots-older-than-days",
            help="Delete price snapshots older than N days.",
        ),
    ] = None,
    news_older_than_days: Annotated[
        int | None,
        typer.Option(
            "--news-older-than-days",
            help="Delete collected news articles older than N days (by collected_at).",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run/--apply",
            help="Preview deletions without applying changes (default: dry-run).",
        ),
    ] = True,
) -> None:
    """Prune old rows to keep the database manageable."""
    from kalshi_research.cli.db import open_db_session
    from kalshi_research.data.maintenance import (
        PruneCounts,
        apply_prune,
        compute_prune_counts,
    )

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        raise typer.Exit(1)

    if snapshots_older_than_days is not None and snapshots_older_than_days < 0:
        console.print("[red]Error:[/red] --snapshots-older-than-days must be >= 0")
        raise typer.Exit(2)
    if news_older_than_days is not None and news_older_than_days < 0:
        console.print("[red]Error:[/red] --news-older-than-days must be >= 0")
        raise typer.Exit(2)

    if snapshots_older_than_days is None and news_older_than_days is None:
        console.print("[red]Error:[/red] No prune targets specified.")
        console.print(
            "[dim]Provide at least one of --snapshots-older-than-days or --news-older-than-days."
            "[/dim]"
        )
        raise typer.Exit(2)

    now = datetime.now(UTC)
    snapshots_before = (
        now - timedelta(days=snapshots_older_than_days)
        if snapshots_older_than_days is not None
        else None
    )
    news_before = (
        now - timedelta(days=news_older_than_days) if news_older_than_days is not None else None
    )

    async def _prune() -> tuple[datetime, PruneCounts]:
        async with open_db_session(db_path) as session:
            if dry_run:
                counts = await compute_prune_counts(
                    session,
                    snapshots_before=snapshots_before,
                    news_before=news_before,
                )
                return (now, counts)

            async with session.begin():
                counts = await apply_prune(
                    session,
                    snapshots_before=snapshots_before,
                    news_before=news_before,
                )
            return (now, counts)

    pruned_at, counts = run_async(_prune())

    table = Table(title="Prune Summary")
    table.add_column("Category", style="cyan")
    table.add_column("Cutoff", style="dim")
    table.add_column("Rows", justify="right", style="green")

    if snapshots_before is not None:
        table.add_row("price_snapshots", snapshots_before.isoformat(), str(counts.price_snapshots))
    if news_before is not None:
        table.add_row("news_articles", news_before.isoformat(), str(counts.news_articles))
        table.add_row(
            "news_article_markets",
            news_before.isoformat(),
            str(counts.news_article_markets),
        )
        table.add_row(
            "news_article_events",
            news_before.isoformat(),
            str(counts.news_article_events),
        )
        table.add_row("news_sentiments", news_before.isoformat(), str(counts.news_sentiments))

    console.print(table)

    mode = "dry-run" if dry_run else "applied"
    console.print(f"[green]✓[/green] Prune {mode} at {pruned_at.isoformat()} (UTC)")


def data_vacuum(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
) -> None:
    """Run SQLite VACUUM to reclaim disk space after large deletes."""
    from sqlalchemy import create_engine, text

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        raise typer.Exit(1)

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT").execute(text("VACUUM"))
    finally:
        engine.dispose()

    console.print("[green]✓[/green] Vacuum complete")
