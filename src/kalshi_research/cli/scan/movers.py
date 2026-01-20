"""Typer CLI command for biggest price movers."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path  # noqa: TC003 - Required at runtime for typer type resolution
from typing import TYPE_CHECKING, Annotated, TypedDict

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from kalshi_research.cli.utils import console, run_async
from kalshi_research.paths import DEFAULT_DB_PATH

if TYPE_CHECKING:
    from kalshi_research.api.models.market import Market


class MoverRow(TypedDict):
    """A row in the movers table."""

    ticker: str
    title: str
    price_change: float
    old_price: float
    new_price: float
    volume: int


# Period map for scan_movers: period string -> hours
_MOVERS_PERIOD_MAP: dict[str, int] = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}


def _parse_movers_period(period: str) -> int:
    """Parse period string to hours, raising Exit(1) on invalid input."""
    if period not in _MOVERS_PERIOD_MAP:
        console.print(f"[red]Error:[/red] Invalid period: {period}. Use 1h, 6h, 24h, or 7d")
        raise typer.Exit(1)
    return _MOVERS_PERIOD_MAP[period]


async def _fetch_movers_market_lookup(
    max_pages: int | None,
) -> dict[str, Market]:
    """Fetch current open markets and return a ticker -> Market lookup."""
    from kalshi_research.cli.client_factory import public_client

    async with public_client() as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Fetching current markets...", total=None)
            markets = [m async for m in client.get_all_markets(status="open", max_pages=max_pages)]

    return {m.ticker: m for m in markets}


async def _compute_movers(
    market_lookup: dict[str, Market],
    db_path: Path,
    hours_back: int,
    period_label: str,
) -> list[MoverRow]:
    """Compute price movers from historical snapshots."""
    from datetime import UTC

    from kalshi_research.cli.db import open_db_session
    from kalshi_research.data.repositories import PriceRepository

    def _as_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)

    movers: list[MoverRow] = []
    async with open_db_session(db_path) as session:
        price_repo = PriceRepository(session)
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours_back)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(f"Analyzing price movements ({period_label})...", total=None)

            for ticker, market in market_lookup.items():
                snapshots = await price_repo.get_for_market(ticker, limit=1000)
                if not snapshots:
                    continue

                recent_snaps = [s for s in snapshots if _as_utc(s.snapshot_time) >= cutoff_time]
                if len(recent_snaps) < 2:
                    continue

                oldest = recent_snaps[-1]
                newest = recent_snaps[0]

                old_prob = oldest.implied_probability
                new_prob = newest.implied_probability
                price_change = new_prob - old_prob

                if abs(price_change) > 0.01:
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

    return movers


def _render_movers_table(
    movers: list[MoverRow],
    period: str,
    *,
    full: bool,
) -> None:
    """Render movers table to console."""
    from rich.console import Console

    table = Table(title=f"Biggest Movers ({period})")
    if full:
        table.add_column("Ticker", style="cyan", no_wrap=True)
        table.add_column("Title", style="white")
    else:
        table.add_column("Ticker", style="cyan", no_wrap=True, overflow="ellipsis", max_width=35)
        table.add_column("Title", style="white", overflow="ellipsis", max_width=40)
    table.add_column("Change", style="yellow")
    table.add_column("Old → New", style="dim")
    table.add_column("Volume", style="magenta")

    for m in movers:
        change_pct = m["price_change"]
        color = "green" if change_pct > 0 else "red"
        arrow = "↑" if change_pct > 0 else "↓"

        table.add_row(
            m["ticker"],
            m["title"],
            f"[{color}]{arrow} {abs(change_pct):.1%}[/{color}]",
            f"{m['old_price']:.1%} → {m['new_price']:.1%}",
            f"{m['volume']:,}",
        )

    output_console = console if not full else Console(width=200)
    output_console.print(table)
    output_console.print(f"\n[dim]Showing top {len(movers)} movers[/dim]")


async def _scan_movers_async(
    *,
    db_path: Path,
    period: str,
    top_n: int,
    max_pages: int | None,
    full: bool,
) -> None:
    """Async implementation of scan_movers."""
    hours_back = _parse_movers_period(period)
    market_lookup = await _fetch_movers_market_lookup(max_pages)
    movers = await _compute_movers(market_lookup, db_path, hours_back, period)

    if not movers:
        console.print(f"[yellow]No significant price movements in the last {period}[/yellow]")
        return

    movers.sort(key=lambda m: abs(m["price_change"]), reverse=True)
    movers = movers[:top_n]

    _render_movers_table(movers, period, full=full)


def scan_movers(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    period: Annotated[str, typer.Option("--period", "-p", help="Time period: 1h, 6h, 24h")] = "24h",
    top_n: Annotated[int, typer.Option("--top", "-n", help="Number of results")] = 10,
    max_pages: Annotated[
        int | None,
        typer.Option(
            "--max-pages",
            help="Optional pagination safety limit for market fetch (None = full).",
        ),
    ] = None,
    full: Annotated[
        bool,
        typer.Option("--full", "-F", help="Show full titles without truncation."),
    ] = False,
) -> None:
    """Show biggest price movers over a time period."""
    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        console.print("[dim]Price history data is required. Run 'kalshi data collect' first.[/dim]")
        raise typer.Exit(1)

    run_async(
        _scan_movers_async(
            db_path=db_path,
            period=period,
            top_n=top_n,
            max_pages=max_pages,
            full=full,
        )
    )
