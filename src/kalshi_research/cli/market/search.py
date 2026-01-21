"""Market search command - search markets in local database by keyword."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from kalshi_research.cli.utils import console, run_async


def market_search(
    query: Annotated[
        str, typer.Argument(help="Search query (keywords to match in title/subtitle).")
    ],
    db: Annotated[
        str,
        typer.Option("--db", help="Path to database file."),
    ] = "data/kalshi.db",
    status: Annotated[
        str | None,
        typer.Option(
            "--status",
            "-s",
            help="Filter by market status (e.g., open, closed, settled).",
        ),
    ] = "open",
    category: Annotated[
        str | None,
        typer.Option(
            "--category",
            "-c",
            help="Filter by category (substring match, case-insensitive).",
        ),
    ] = None,
    event: Annotated[
        str | None,
        typer.Option("--event", "-e", help="Filter by exact event ticker."),
    ] = None,
    series: Annotated[
        str | None,
        typer.Option("--series", help="Filter by exact series ticker."),
    ] = None,
    min_volume: Annotated[
        int | None,
        typer.Option("--min-volume", help="Minimum 24h volume (requires price snapshot)."),
    ] = None,
    max_spread: Annotated[
        int | None,
        typer.Option("--max-spread", help="Maximum spread in cents (requires price snapshot)."),
    ] = None,
    top: Annotated[
        int,
        typer.Option("--top", "-n", help="Maximum number of results to return."),
    ] = 20,
    format_output: Annotated[
        str,
        typer.Option("--format", help="Output format: table or json."),
    ] = "table",
) -> None:
    """Search markets in the local database by keyword.

    Uses FTS5 full-text search if available, otherwise falls back to LIKE queries.
    Searches are performed on the local database, not the live API.

    Run 'kalshi data sync-markets' first to populate/update the database.
    """
    run_async(
        _market_search_async(
            query=query,
            db=db,
            status=status,
            category=category,
            event=event,
            series=series,
            min_volume=min_volume,
            max_spread=max_spread,
            top=top,
            format_output=format_output,
        )
    )


async def _market_search_async(
    *,
    query: str,
    db: str,
    status: str | None,
    category: str | None,
    event: str | None,
    series: str | None,
    min_volume: int | None,
    max_spread: int | None,
    top: int,
    format_output: str,
) -> None:
    """Async implementation of market search."""
    import json
    from pathlib import Path

    from kalshi_research.cli.db import open_db_session
    from kalshi_research.data.repositories.search import SearchRepository
    from kalshi_research.data.search_utils import has_fts5_support

    db_path = Path(db)
    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database file not found: {db}")
        console.print(
            "[dim]Run 'kalshi data init' to create the database, "
            "then 'kalshi data sync-markets' to populate it.[/dim]"
        )
        raise typer.Exit(1)

    async with open_db_session(db_path) as session:
        # Check FTS5 support and warn if unavailable
        has_fts5 = await has_fts5_support(session)
        if not has_fts5:
            console.print(
                "[yellow]Warning:[/yellow] FTS5 not available. Using slower LIKE-based search."
            )

        search_repo = SearchRepository(session)
        results = await search_repo.search_markets(
            query,
            status=status,
            category=category,
            event_ticker=event,
            series_ticker=series,
            min_volume=min_volume,
            max_spread=max_spread,
            limit=top,
        )

    if not results:
        console.print("[yellow]No markets found.[/yellow]")
        return

    if format_output == "json":
        # Output as JSON
        json_results = [
            {
                "ticker": r.ticker,
                "title": r.title,
                "subtitle": r.subtitle,
                "event_ticker": r.event_ticker,
                "event_category": r.event_category,
                "status": r.status,
                "midpoint": r.midpoint,
                "spread": r.spread,
                "volume_24h": r.volume_24h,
                "close_time": r.close_time.isoformat(),
                "expiration_time": r.expiration_time.isoformat(),
            }
            for r in results
        ]
        typer.echo(json.dumps(json_results, indent=2))
    else:
        # Output as table
        table = Table(title=f"Search Results: '{query}' ({len(results)} found)")
        table.add_column("Ticker", style="cyan", no_wrap=True)
        table.add_column("Title", style="white")
        table.add_column("Category", style="magenta")
        table.add_column("Status", style="yellow")
        table.add_column("Mid%", justify="right", style="green")
        table.add_column("Spread", justify="right", style="dim")
        table.add_column("Vol24h", justify="right", style="blue")

        for result in results:
            mid_display = f"{result.midpoint:.1f}" if result.midpoint is not None else "—"
            spread_display = f"{result.spread}¢" if result.spread is not None else "—"
            vol_display = f"{result.volume_24h:,}" if result.volume_24h is not None else "—"

            table.add_row(
                result.ticker,
                result.title[:60] + "..." if len(result.title) > 60 else result.title,
                result.event_category or "—",
                result.status,
                mid_display,
                spread_display,
                vol_display,
            )

        console.print(table)
