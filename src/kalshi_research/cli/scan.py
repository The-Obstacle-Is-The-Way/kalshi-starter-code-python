import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from kalshi_research.cli.utils import console
from kalshi_research.paths import DEFAULT_DB_PATH

app = typer.Typer(help="Market scanning commands.")


@app.command("opportunities")
def scan_opportunities(
    filter_type: Annotated[
        str | None,
        typer.Option(
            "--filter",
            "-f",
            help="Filter type: close-race, high-volume, wide-spread, expiring-soon",
        ),
    ] = None,
    top_n: Annotated[int, typer.Option("--top", "-n", help="Number of results")] = 10,
    min_volume: Annotated[
        int,
        typer.Option(
            "--min-volume",
            help="Minimum 24h volume (close-race filter only).",
        ),
    ] = 0,
    max_spread: Annotated[
        int,
        typer.Option(
            "--max-spread",
            help="Maximum bid-ask spread in cents (close-race filter only).",
        ),
    ] = 100,
    max_pages: Annotated[
        int | None,
        typer.Option(
            "--max-pages",
            help="Optional pagination safety limit for market fetch (None = full).",
        ),
    ] = None,
) -> None:
    """Scan markets for opportunities."""
    from kalshi_research.analysis.scanner import MarketScanner
    from kalshi_research.api import KalshiPublicClient

    async def _scan() -> None:
        async with KalshiPublicClient() as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Fetching markets...", total=None)
                # Fetch all open markets for scanning
                markets = [
                    m async for m in client.get_all_markets(status="open", max_pages=max_pages)
                ]

        scanner = MarketScanner()

        if filter_type:
            if filter_type == "close-race":
                results = scanner.scan_close_races(
                    markets,
                    top_n,
                    min_volume_24h=min_volume,
                    max_spread=max_spread,
                )
                title = "Scan Results (close-race)"
            elif filter_type == "high-volume":
                results = scanner.scan_high_volume(markets, top_n)
                title = "Scan Results (high-volume)"
            elif filter_type == "wide-spread":
                results = scanner.scan_wide_spread(markets, top_n)
                title = "Scan Results (wide-spread)"
            elif filter_type == "expiring-soon":
                results = scanner.scan_expiring_soon(markets, top_n)
                title = "Scan Results (expiring-soon)"
            else:
                console.print(f"[red]Error:[/red] Unknown filter: {filter_type}")
                raise typer.Exit(1)
        else:
            # Default to "interesting" markets logic (e.g. close races for now)
            # In a real impl, this might combine multiple signals
            results = scanner.scan_close_races(
                markets,
                top_n,
                min_volume_24h=min_volume,
                max_spread=max_spread,
            )
            title = "Scan Results (Close Races)"

        if not results:
            console.print("[yellow]No markets found matching criteria.[/yellow]")
            return

        table = Table(title=title)
        table.add_column("Ticker", style="cyan", no_wrap=True)
        table.add_column("Title", style="white")
        table.add_column("Probability", style="green")
        table.add_column("Spread", style="yellow")
        table.add_column("Volume", style="magenta")

        for m in results:
            table.add_row(
                m.ticker,
                m.title[:50],
                f"{m.market_prob:.1%}",
                f"{m.spread}¢",
                f"{m.volume_24h:,}",
            )

        console.print(table)

    asyncio.run(_scan())


@app.command("arbitrage")
def scan_arbitrage(  # noqa: PLR0915
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
) -> None:
    """Find arbitrage opportunities from correlated markets."""
    from kalshi_research.analysis.correlation import CorrelationAnalyzer, CorrelationResult
    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.api.models.market import Market
    from kalshi_research.data import DatabaseManager

    if not db_path.exists():
        console.print(
            "[yellow]Warning:[/yellow] Database not found, analyzing current markets only"
        )

    async def _load_correlated_pairs(markets: list[Market]) -> list[CorrelationResult]:
        if not db_path.exists():
            return []

        from kalshi_research.data.repositories import PriceRepository

        async with DatabaseManager(db_path) as db, db.session_factory() as session:
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

                snapshots = {}
                for ticker in tickers:
                    snaps = await price_repo.get_for_market(ticker, limit=100)
                    if snaps and len(snaps) > 30:
                        snapshots[ticker] = list(snaps)

            if len(snapshots) < 2:
                return []

            analyzer = CorrelationAnalyzer(min_correlation=0.5)
            return await analyzer.find_correlated_markets(snapshots, top_n=50)

    async def _scan() -> None:
        # Fetch current markets
        async with KalshiPublicClient() as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Fetching markets...", total=None)
                markets = [
                    m async for m in client.get_all_markets(status="open", max_pages=max_pages)
                ]

        if not markets:
            console.print("[yellow]No open markets found[/yellow]")
            return

        correlated_pairs = await _load_correlated_pairs(markets)

        analyzer = CorrelationAnalyzer()

        # Find arbitrage opportunities
        opportunities = analyzer.find_arbitrage_opportunities(
            markets, correlated_pairs, divergence_threshold=divergence_threshold
        )

        # Combine with inverse pairs
        for m1, m2, deviation in analyzer.find_inverse_markets(
            markets, tolerance=divergence_threshold
        ):
            from kalshi_research.analysis.correlation import ArbitrageOpportunity

            opportunities.append(
                ArbitrageOpportunity(
                    tickers=[m1.ticker, m2.ticker],
                    opportunity_type="inverse_sum",
                    expected_relationship="Sum to ~100%",
                    actual_values={
                        m1.ticker: m1.midpoint / 100.0,
                        m2.ticker: m2.midpoint / 100.0,
                        "sum": m1.midpoint / 100.0 + m2.midpoint / 100.0,
                    },
                    divergence=abs(deviation),
                    confidence=0.95,
                )
            )

        if not opportunities:
            console.print("[yellow]No arbitrage opportunities found[/yellow]")
            return

        # Sort by divergence
        opportunities.sort(key=lambda o: o.divergence, reverse=True)
        opportunities = opportunities[:top_n]

        # Display results
        table = Table(title="Arbitrage Opportunities")
        table.add_column("Tickers", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Expected", style="dim")
        table.add_column("Divergence", style="red")
        table.add_column("Confidence", style="green")

        for opp in opportunities:
            tickers_str = ", ".join(opp.tickers[:2])
            table.add_row(
                tickers_str[:30],
                opp.opportunity_type,
                opp.expected_relationship[:40],
                f"{opp.divergence:.2%}",
                f"{opp.confidence:.2f}",
            )

        console.print(table)
        console.print(f"\n[dim]Found {len(opportunities)} opportunities[/dim]")

    asyncio.run(_scan())


@app.command("movers")
def scan_movers(  # noqa: PLR0915
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
) -> None:
    """Show biggest price movers over a time period."""

    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.data import DatabaseManager

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        console.print("[dim]Price history data is required. Run 'kalshi data collect' first.[/dim]")
        raise typer.Exit(1)

    # Parse period
    period_map = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}
    if period not in period_map:
        console.print(f"[red]Error:[/red] Invalid period: {period}. Use 1h, 6h, 24h, or 7d")
        raise typer.Exit(1)

    hours_back = period_map[period]

    async def _scan() -> None:
        from datetime import UTC

        from kalshi_research.data.repositories import PriceRepository

        def _as_utc(dt: datetime) -> datetime:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)

        # Get current markets
        async with KalshiPublicClient() as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Fetching current markets...", total=None)
                markets = [
                    m async for m in client.get_all_markets(status="open", max_pages=max_pages)
                ]

        market_lookup = {m.ticker: m for m in markets}

        # Get historical prices
        movers: list[dict[str, Any]] = []
        async with DatabaseManager(db_path) as db, db.session_factory() as session:
            price_repo = PriceRepository(session)

            cutoff_time = datetime.now(UTC) - timedelta(hours=hours_back)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(f"Analyzing price movements ({period})...", total=None)

                for ticker, market in market_lookup.items():
                    # Get snapshots from the period
                    snapshots = await price_repo.get_for_market(ticker, limit=1000)

                    if not snapshots:
                        continue

                    # Filter to time range
                    recent_snaps = [s for s in snapshots if _as_utc(s.snapshot_time) >= cutoff_time]
                    if len(recent_snaps) < 2:
                        continue

                    # Calculate price change
                    oldest = recent_snaps[-1]  # Oldest in range
                    newest = recent_snaps[0]  # Most recent

                    old_prob = oldest.implied_probability
                    new_prob = newest.implied_probability
                    price_change = new_prob - old_prob

                    if abs(price_change) > 0.01:  # At least 1% move
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

        if not movers:
            console.print(f"[yellow]No significant price movements in the last {period}[/yellow]")
            return

        # Sort by absolute change
        movers.sort(key=lambda m: abs(m["price_change"]), reverse=True)
        movers = movers[:top_n]

        # Display results
        table = Table(title=f"Biggest Movers ({period})")
        table.add_column("Ticker", style="cyan", no_wrap=True)
        table.add_column("Title", style="white")
        table.add_column("Change", style="yellow")
        table.add_column("Old → New", style="dim")
        table.add_column("Volume", style="magenta")

        for m in movers:
            change_pct = m["price_change"]
            color = "green" if change_pct > 0 else "red"
            arrow = "↑" if change_pct > 0 else "↓"

            table.add_row(
                m["ticker"],
                m["title"][:40],
                f"[{color}]{arrow} {abs(change_pct):.1%}[/{color}]",
                f"{m['old_price']:.1%} → {m['new_price']:.1%}",
                f"{m['volume']:,}",
            )

        console.print(table)
        console.print(f"\n[dim]Showing top {len(movers)} movers[/dim]")

    asyncio.run(_scan())
