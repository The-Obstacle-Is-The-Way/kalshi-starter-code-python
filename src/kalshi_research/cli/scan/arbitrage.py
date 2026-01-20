"""Typer CLI command for arbitrage detection."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated, cast

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from kalshi_research.cli.utils import console, run_async
from kalshi_research.paths import DEFAULT_DB_PATH

if TYPE_CHECKING:
    from kalshi_research.analysis.correlation import ArbitrageOpportunity, CorrelationResult
    from kalshi_research.api.models.market import Market
    from kalshi_research.data.models import PriceSnapshot


async def _load_correlated_pairs(
    markets: list[Market],
    *,
    db_path: Path,
    tickers_limit: int,
) -> list[CorrelationResult]:
    """Load correlated market pairs from historical price data."""
    if not db_path.exists():
        return []

    from kalshi_research.analysis.correlation import CorrelationAnalyzer
    from kalshi_research.cli.db import open_db_session
    from kalshi_research.data.repositories import PriceRepository

    async with open_db_session(db_path) as session:
        price_repo = PriceRepository(session)

        tickers = [m.ticker for m in markets]
        if tickers_limit > 0 and len(tickers) > tickers_limit:
            console.print(
                "[yellow]Warning:[/yellow] Limiting correlation analysis to first "
                f"{tickers_limit} tickers (out of {len(tickers)}). "
                "Use --tickers-limit to adjust."
            )
            tickers = tickers[:tickers_limit]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Analyzing correlations...", total=None)

            snapshots: dict[str, list[PriceSnapshot]] = {}
            for ticker in tickers:
                snaps = await price_repo.get_for_market(ticker, limit=100)
                if snaps and len(snaps) > 30:
                    snapshots[ticker] = list(snaps)

        if len(snapshots) < 2:
            return []

        analyzer = CorrelationAnalyzer(min_correlation=0.5)
        return await analyzer.find_correlated_markets(snapshots, top_n=50)


def _render_arbitrage_opportunities_table(
    opportunities: list[ArbitrageOpportunity],
    *,
    full: bool,
) -> None:
    """Render arbitrage opportunities table to console."""
    from rich.console import Console

    table = Table(title="Arbitrage Opportunities")
    if full:
        table.add_column("Tickers", style="cyan", no_wrap=True)
    else:
        table.add_column("Tickers", style="cyan", no_wrap=True, overflow="ellipsis", max_width=30)
    table.add_column("Type", style="yellow")
    if full:
        table.add_column("Expected", style="dim")
    else:
        table.add_column("Expected", style="dim", overflow="ellipsis", max_width=40)
    table.add_column("Divergence", style="red")
    table.add_column("Confidence", style="green")

    for opp in opportunities:
        tickers_str = _format_opportunity_tickers(opp.tickers, full=full)
        table.add_row(
            tickers_str,
            opp.opportunity_type,
            opp.expected_relationship,
            f"{opp.divergence:.2%}",
            f"{opp.confidence:.2f}",
        )

    output_console = console if not full else Console(width=200)
    output_console.print(table)
    output_console.print(f"\n[dim]Found {len(opportunities)} opportunities[/dim]")


def _format_opportunity_tickers(tickers: list[str], *, full: bool) -> str:
    """Format ticker list for display, truncating if needed."""
    if full or len(tickers) <= 2:
        return ", ".join(tickers)

    extra = len(tickers) - 2
    return f"{', '.join(tickers[:2])}, +{extra}"


async def _scan_arbitrage_async(
    *,
    db_path: Path,
    divergence_threshold: float,
    top_n: int,
    tickers_limit: int,
    max_pages: int | None,
    full: bool,
) -> None:
    """Async implementation of scan_arbitrage."""
    from kalshi_research.analysis.correlation import ArbitrageOpportunity, CorrelationAnalyzer
    from kalshi_research.cli.client_factory import public_client

    if not db_path.exists():
        console.print(
            "[yellow]Warning:[/yellow] Database not found, analyzing current markets only"
        )

    async with public_client() as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Fetching markets...", total=None)
            markets = [m async for m in client.get_all_markets(status="open", max_pages=max_pages)]

    if not markets:
        console.print("[yellow]No open markets found[/yellow]")
        return

    correlated_pairs = await _load_correlated_pairs(
        markets, db_path=db_path, tickers_limit=tickers_limit
    )

    analyzer = CorrelationAnalyzer()

    opportunities = analyzer.find_arbitrage_opportunities(
        markets, correlated_pairs, divergence_threshold=divergence_threshold
    )

    for group_markets, deviation in analyzer.find_inverse_market_groups(
        markets, tolerance=divergence_threshold
    ):
        prices: dict[str, float] = {}
        for m in group_markets:
            midpoint = cast("float", m.midpoint)
            prices[m.ticker] = midpoint / 100.0
        prices["sum"] = sum(prices[m.ticker] for m in group_markets)
        opportunities.append(
            ArbitrageOpportunity(
                tickers=[m.ticker for m in group_markets],
                opportunity_type="inverse_sum",
                expected_relationship="Sum to ~100%",
                actual_values=prices,
                divergence=abs(deviation),
                confidence=0.95,
            )
        )

    if not opportunities:
        console.print("[yellow]No arbitrage opportunities found[/yellow]")
        return

    opportunities.sort(key=lambda o: o.divergence, reverse=True)
    opportunities = opportunities[:top_n]

    _render_arbitrage_opportunities_table(opportunities, full=full)


def scan_arbitrage(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    divergence_threshold: Annotated[
        float, typer.Option("--threshold", help="Min divergence to flag (0-1)")
    ] = 0.10,
    top_n: Annotated[int, typer.Option("--top", "-n", help="Number of results")] = 10,
    tickers_limit: Annotated[
        int,
        typer.Option(
            "--tickers-limit",
            help="Limit historical correlation analysis to N tickers (0 = analyze all tickers).",
        ),
    ] = 50,
    max_pages: Annotated[
        int | None,
        typer.Option(
            "--max-pages",
            help="Optional pagination safety limit for market fetch (None = full).",
        ),
    ] = None,
    full: Annotated[
        bool,
        typer.Option("--full", "-F", help="Show full tickers/relationships without truncation."),
    ] = False,
) -> None:
    """Find arbitrage opportunities from correlated markets."""
    db_path = Path(db_path)
    run_async(
        _scan_arbitrage_async(
            db_path=db_path,
            divergence_threshold=divergence_threshold,
            top_n=top_n,
            tickers_limit=tickers_limit,
            max_pages=max_pages,
            full=full,
        )
    )
