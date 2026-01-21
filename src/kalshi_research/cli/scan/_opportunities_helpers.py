"""Helper functions for opportunities scan command."""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.table import Table

from kalshi_research.cli.utils import console

if TYPE_CHECKING:
    from datetime import datetime

    from kalshi_research.analysis.scanner import MarketScanner, ScanResult
    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.api.models.market import Market


class ScanProfile(str, Enum):
    """Opinionated presets for `kalshi scan opportunities`."""

    RAW = "raw"
    TRADEABLE = "tradeable"
    LIQUID = "liquid"
    EARLY = "early"


def scan_profile_defaults(profile: ScanProfile) -> tuple[int, int, int | None]:
    """Return (min_volume, max_spread, min_liquidity) defaults for the given profile."""
    if profile is ScanProfile.RAW:
        return 0, 100, None
    if profile is ScanProfile.TRADEABLE:
        return 1000, 10, None
    if profile is ScanProfile.LIQUID:
        return 5000, 5, 60
    if profile is ScanProfile.EARLY:
        return 100, 5, 40
    raise ValueError(f"Unknown ScanProfile: {profile}")


def filter_markets_by_age(
    markets: list[Market],
    *,
    cutoff: datetime,
) -> tuple[list[Market], int]:
    """Filter markets by age, returning those created/opened after cutoff.

    Returns:
        Tuple of (filtered_markets, missing_created_time_count).
    """
    filtered_markets: list[Market] = []
    missing_created_time = 0

    for market in markets:
        reference_time = market.created_time or market.open_time
        if reference_time < cutoff:
            continue
        if market.created_time is None:
            missing_created_time += 1
        filtered_markets.append(market)

    return filtered_markets, missing_created_time


def select_opportunity_results(
    scanner: MarketScanner,
    markets: list[Market],
    *,
    filter_type: str | None,
    top_n: int,
    min_volume: int,
    max_spread: int,
) -> tuple[list[ScanResult], str]:
    """Select markets using the specified filter type."""
    if filter_type is None:
        return (
            scanner.scan_close_races(
                markets,
                top_n,
                min_volume_24h=min_volume,
                max_spread=max_spread,
            ),
            "Scan Results (Close Races)",
        )

    if filter_type == "close-race":
        return (
            scanner.scan_close_races(
                markets,
                top_n,
                min_volume_24h=min_volume,
                max_spread=max_spread,
            ),
            "Scan Results (close-race)",
        )
    if filter_type == "high-volume":
        return scanner.scan_high_volume(markets, top_n), "Scan Results (high-volume)"
    if filter_type == "wide-spread":
        return scanner.scan_wide_spread(markets, top_n), "Scan Results (wide-spread)"
    if filter_type == "expiring-soon":
        return scanner.scan_expiring_soon(markets, top_n=top_n), "Scan Results (expiring-soon)"

    console.print(f"[red]Error:[/red] Unknown filter: {filter_type}")
    raise typer.Exit(1)


def filter_results_by_liquidity(
    results: list[ScanResult],
    liquidity_by_ticker: dict[str, int],
    *,
    min_liquidity: int,
    top_n: int,
) -> list[ScanResult]:
    """Filter scan results by minimum liquidity score."""
    filtered = [r for r in results if liquidity_by_ticker.get(r.ticker, 0) >= min_liquidity]
    return filtered[:top_n]


def render_opportunities_table(
    results: list[ScanResult],
    title: str,
    *,
    full: bool,
    show_liquidity: bool,
    min_liquidity: int | None,
    liquidity_by_ticker: dict[str, int],
) -> None:
    """Render opportunity scan results table to console."""
    output_console = console if not full else Console(width=200)

    table = Table(title=title)
    if full:
        table.add_column("Ticker", style="cyan", no_wrap=True)
        table.add_column("Title", style="white")
    else:
        table.add_column("Ticker", style="cyan", no_wrap=True, overflow="ellipsis", max_width=35)
        table.add_column("Title", style="white", overflow="ellipsis", max_width=50)
    table.add_column("Probability", style="green")
    table.add_column("Spread", style="yellow")
    table.add_column("Volume", style="magenta")
    if show_liquidity or min_liquidity is not None:
        table.add_column("Liquidity", style="blue", justify="right")

    for m in results:
        row = [
            m.ticker,
            m.title,
            f"{m.market_prob:.1%}",
            f"{m.spread}¢",
            f"{m.volume_24h:,}",
        ]
        if show_liquidity or min_liquidity is not None:
            score = liquidity_by_ticker.get(m.ticker)
            row.append(f"{score}" if score is not None else "N/A")
        table.add_row(*row)

    output_console.print(table)


async def fetch_exchange_status(
    client: KalshiPublicClient,
) -> dict[str, object] | None:
    """Fetch and sanity-check the exchange status response.

    Returns `None` when the status cannot be fetched or does not contain the expected boolean
    fields, allowing scans to proceed without exchange-halt checks.
    """
    try:
        raw_status = await client.get_exchange_status()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        console.print(
            "[yellow]Warning:[/yellow] Failed to fetch exchange status; proceeding without "
            f"exchange halt checks ({exc})."
        )
        return None

    if not isinstance(raw_status, dict):
        console.print(
            "[yellow]Warning:[/yellow] Exchange status response had unexpected type; "
            "proceeding without exchange halt checks."
        )
        return None

    exchange_active = raw_status.get("exchange_active")
    trading_active = raw_status.get("trading_active")
    if isinstance(exchange_active, bool) and isinstance(trading_active, bool):
        return raw_status

    console.print(
        "[yellow]Warning:[/yellow] Exchange status response was missing expected boolean fields; "
        "proceeding without exchange halt checks."
    )
    return None
