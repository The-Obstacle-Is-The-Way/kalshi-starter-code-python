"""Shared helper functions and types for scan CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

import typer
from rich.console import Console
from rich.table import Table

from kalshi_research.cli.utils import console

if TYPE_CHECKING:
    from datetime import datetime

    from kalshi_research.api.models.market import Market


class NewMarketRow(TypedDict):
    """A row in the new markets table."""

    ticker: str
    title: str
    event_ticker: str
    status: str
    yes_bid_cents: int | None
    yes_ask_cents: int | None
    yes_price_display: str
    category: str
    created_time: str
    age: str


def format_relative_age(*, now: datetime, timestamp: datetime) -> str:
    """Format a timestamp as relative age (e.g., '2h ago', 'in 5m')."""
    seconds = int((now - timestamp).total_seconds())
    in_future = seconds < 0
    seconds = abs(seconds)

    if seconds < 60:
        value = seconds
        unit = "s"
    elif seconds < 60 * 60:
        value = seconds // 60
        unit = "m"
    elif seconds < 60 * 60 * 48:
        value = seconds // (60 * 60)
        unit = "h"
    else:
        value = seconds // (60 * 60 * 24)
        unit = "d"

    if in_future:
        return f"in {value}{unit}"
    return f"{value}{unit} ago"


def parse_category_filter(category: str | None) -> set[str] | None:
    """Parse a comma-separated category filter into normalized, lowercase tokens."""
    if category is None:
        return None

    parts = [p.strip() for p in category.split(",")]
    parts = [p for p in parts if p]
    if not parts:
        return None

    from kalshi_research.analysis.categories import normalize_category

    normalized = {normalize_category(p).strip().lower() for p in parts}
    return {p for p in normalized if p}


def is_unpriced_market(market: Market) -> bool:
    """Check if a market has placeholder pricing (no real price discovery)."""
    bid = market.yes_bid_cents
    ask = market.yes_ask_cents
    if bid is None or ask is None:
        return True
    return (bid == 0 and ask == 0) or (bid == 0 and ask == 100)


def market_yes_price_display(market: Market) -> str:
    """Format the yes price for display."""
    bid = market.yes_bid_cents
    ask = market.yes_ask_cents
    if bid is None or ask is None:
        return "[MISSING PRICE]"
    if bid == 0 and ask == 0:
        return "[NO QUOTES]"
    if bid == 0 and ask == 100:
        return "[AWAITING PRICE DISCOVERY]"
    midpoint = (bid + ask) / 2
    if midpoint.is_integer():
        return f"{int(midpoint)}¢"
    return f"{midpoint:.1f}¢"


def validate_new_markets_args(*, hours: int, limit: int) -> None:
    """Validate `new-markets` CLI arguments and exit on invalid values."""
    if hours <= 0:
        console.print("[red]Error:[/red] --hours must be positive.")
        raise typer.Exit(1)
    if limit <= 0:
        console.print("[red]Error:[/red] --limit must be positive.")
        raise typer.Exit(1)


def render_new_markets_table(
    results: list[NewMarketRow],
    *,
    hours: int,
    full: bool,
    skipped_unpriced: int,
    unpriced_included: int,
) -> None:
    """Render new markets table to console."""
    table = Table(title=f"New Markets (last {hours} hours)")
    if full:
        table.add_column("Ticker", style="cyan", no_wrap=True)
        table.add_column("Status", style="dim", no_wrap=True)
        table.add_column("Title", style="white")
    else:
        table.add_column("Ticker", style="cyan", no_wrap=True, overflow="ellipsis", max_width=35)
        table.add_column("Status", style="dim", no_wrap=True)
        table.add_column("Title", style="white", overflow="ellipsis", max_width=50)
    table.add_column("Yes", style="green", no_wrap=True)
    table.add_column("Category", style="magenta", overflow="ellipsis", max_width=22)
    table.add_column("Created", style="dim", no_wrap=True)

    for item in results:
        table.add_row(
            str(item["ticker"]),
            str(item["status"]),
            str(item["title"]),
            str(item["yes_price_display"]),
            str(item["category"]),
            str(item["age"]),
        )

    output_console = console if not full else Console(width=200)
    output_console.print(table)

    summary_bits: list[str] = []
    if unpriced_included:
        summary_bits.append(f"{unpriced_included} unpriced")
    if skipped_unpriced:
        summary_bits.append(f"skipped {skipped_unpriced} unpriced; use --include-unpriced")

    summary = f"[dim]Showing {len(results)} new markets[/dim]"
    if summary_bits:
        summary = f"{summary} [dim]({'; '.join(summary_bits)})[/dim]"
    output_console.print(f"\n{summary}")
