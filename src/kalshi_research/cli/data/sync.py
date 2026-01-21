"""Data synchronization commands (sync-markets, sync-settlements, sync-trades)."""

import csv
import json
from pathlib import Path
from typing import Annotated, Literal, cast

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from kalshi_research.cli.utils import console, exit_kalshi_api_error, run_async
from kalshi_research.paths import DEFAULT_DB_PATH


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
    mve_filter: Annotated[
        str | None,
        typer.Option(
            "--mve-filter",
            help="Filter multivariate events: 'exclude' (skip sports parlays) or 'only'.",
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
    """Sync markets from Kalshi API to database."""
    from kalshi_research.cli.db import open_db
    from kalshi_research.data import DataFetcher

    # Validate mve_filter value
    mve_filter_typed: Literal["only", "exclude"] | None = None
    if mve_filter is not None:
        if mve_filter not in ("only", "exclude"):
            console.print(
                f"[red]Error:[/red] --mve-filter must be 'only' or 'exclude', got '{mve_filter}'"
            )
            raise typer.Exit(1)
        mve_filter_typed = cast("Literal['only', 'exclude']", mve_filter)

    async def _sync() -> None:
        async with open_db(db_path) as db, DataFetcher(db) as fetcher:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task1 = progress.add_task("Syncing events...", total=None)
                events = await fetcher.sync_events(
                    max_pages=max_pages,
                    include_multivariate=include_mve_events,
                )
                progress.update(task1, description=f"Synced {events} events")

                progress.add_task("Syncing markets...", total=None)
                markets = await fetcher.sync_markets(
                    status=status, max_pages=max_pages, mve_filter=mve_filter_typed
                )

        console.print(f"[green]✓[/green] Synced {events} events and {markets} markets")

    run_async(_sync())


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
        Kalshi exposes `settlement_ts` (added Dec 19, 2025) for settled markets.
        We store `Settlement.settled_at` using `Market.settlement_ts` when available, falling back
        to `Market.expiration_time` for historical/legacy data.
    """
    from kalshi_research.cli.db import open_db
    from kalshi_research.data import DataFetcher

    async def _sync() -> None:
        async with open_db(db_path) as db, DataFetcher(db) as fetcher:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Syncing settlements...", total=None)
                settlements = await fetcher.sync_settlements(max_pages=max_pages)

        console.print(f"[green]✓[/green] Synced {settlements} settlements")

    run_async(_sync())


def data_sync_trades(
    ticker: Annotated[
        str | None,
        typer.Option("--ticker", help="Optional market ticker filter."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Max trades to fetch (Kalshi caps at 1000)."),
    ] = 100,
    min_ts: Annotated[
        int | None,
        typer.Option("--min-ts", help="Filter: min Unix timestamp (seconds)."),
    ] = None,
    max_ts: Annotated[
        int | None,
        typer.Option("--max-ts", help="Filter: max Unix timestamp (seconds)."),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Write results to a CSV file."),
    ] = None,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output results as JSON to stdout."),
    ] = False,
) -> None:
    """Fetch public trade history from Kalshi (GET /markets/trades)."""
    from kalshi_research.api.exceptions import KalshiAPIError
    from kalshi_research.cli.client_factory import public_client

    if output is not None and output_json:
        console.print("[red]Error:[/red] Choose one of --output or --json (not both).")
        raise typer.Exit(2)

    async def _fetch() -> list[dict[str, object]]:
        async with public_client() as client:
            try:
                trades = await client.get_trades(
                    ticker=ticker,
                    limit=limit,
                    min_ts=min_ts,
                    max_ts=max_ts,
                )
            except KalshiAPIError as e:
                exit_kalshi_api_error(e)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        return [t.model_dump(mode="json") for t in trades]

    trade_rows = run_async(_fetch())

    if output_json:
        typer.echo(json.dumps(trade_rows, indent=2, default=str))
        return

    if output is None:
        if not trade_rows:
            console.print("[yellow]No trades returned for the given filters.[/yellow]")
            return
        table = Table(title="Trades")
        table.add_column("Ticker", style="cyan", no_wrap=True)
        table.add_column("Time", style="dim")
        table.add_column("YES", justify="right", style="green")
        table.add_column("NO", justify="right", style="red")
        table.add_column("Qty", justify="right", style="magenta")
        table.add_column("Taker", style="white")

        for row in trade_rows[:25]:
            table.add_row(
                str(row.get("ticker", "")),
                str(row.get("created_time", "")),
                str(row.get("yes_price", "")),
                str(row.get("no_price", "")),
                str(row.get("count", "")),
                str(row.get("taker_side", "")),
            )

        console.print(table)
        if len(trade_rows) > 25:
            console.print(
                f"[dim]Showing 25 of {len(trade_rows)} trades. Use --output to export.[/dim]"
            )
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "trade_id",
        "ticker",
        "created_time",
        "yes_price",
        "no_price",
        "count",
        "taker_side",
    ]
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in trade_rows:
            writer.writerow({k: row.get(k) for k in fieldnames})

    console.print(f"[green]✓[/green] Exported {len(trade_rows)} trades to {output}")
