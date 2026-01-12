from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, TypedDict

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from kalshi_research.cli.utils import console
from kalshi_research.paths import DEFAULT_DB_PATH

app = typer.Typer(help="Market scanning commands.")


if TYPE_CHECKING:
    from kalshi_research.analysis.correlation import ArbitrageOpportunity, CorrelationResult
    from kalshi_research.analysis.scanner import MarketScanner, ScanResult
    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.api.models.market import Market
    from kalshi_research.data.models import PriceSnapshot


class MoverRow(TypedDict):
    ticker: str
    title: str
    price_change: float
    old_price: float
    new_price: float
    volume: int


def _select_opportunity_results(
    scanner: MarketScanner,
    markets: list[Market],
    *,
    filter_type: str | None,
    top_n: int,
    min_volume: int,
    max_spread: int,
) -> tuple[list[ScanResult], str]:
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


async def _compute_liquidity_scores(
    client: KalshiPublicClient,
    markets_by_ticker: dict[str, Market],
    results: list[ScanResult],
    *,
    liquidity_depth: int,
) -> dict[str, int]:
    from kalshi_research.analysis.liquidity import liquidity_score
    from kalshi_research.api.exceptions import KalshiAPIError

    scores: dict[str, int] = {}

    for r in results:
        market = markets_by_ticker.get(r.ticker)
        if market is None:
            continue
        try:
            orderbook = await client.get_orderbook(r.ticker, depth=liquidity_depth)
        except KalshiAPIError as e:
            console.print(
                f"[yellow]Warning:[/yellow] Skipping liquidity for {r.ticker}: "
                f"API Error {e.status_code}: {e.message}"
            )
            continue

        scores[r.ticker] = liquidity_score(market, orderbook).score

    return scores


def _filter_results_by_liquidity(
    results: list[ScanResult],
    liquidity_by_ticker: dict[str, int],
    *,
    min_liquidity: int,
    top_n: int,
) -> list[ScanResult]:
    filtered = [r for r in results if liquidity_by_ticker.get(r.ticker, 0) >= min_liquidity]
    return filtered[:top_n]


def _render_opportunities_table(
    results: list[ScanResult],
    title: str,
    *,
    full: bool,
    show_liquidity: bool,
    min_liquidity: int | None,
    liquidity_by_ticker: dict[str, int],
) -> None:
    from rich.console import Console

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


async def _fetch_exchange_status(
    client: KalshiPublicClient,
) -> dict[str, object] | None:
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


async def _scan_opportunities_async(
    *,
    filter_type: str | None,
    category: str | None,
    no_sports: bool,
    event_prefix: str | None,
    full: bool,
    top_n: int,
    min_volume: int,
    max_spread: int,
    max_pages: int | None,
    min_liquidity: int | None,
    show_liquidity: bool,
    liquidity_depth: int,
) -> None:
    from kalshi_research.analysis.scanner import MarketScanner
    from kalshi_research.api import KalshiPublicClient

    scan_top_n = top_n if min_liquidity is None else min(top_n * 5, 50)

    async with KalshiPublicClient() as client:
        exchange_status = await _fetch_exchange_status(client)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Fetching markets...", total=None)
            if category or no_sports or event_prefix:
                from kalshi_research.analysis.categories import SPORTS_CATEGORY, normalize_category

                include_category = normalize_category(category) if category else None
                include_lower = include_category.strip().lower() if include_category else None
                prefix_upper = event_prefix.upper() if event_prefix else None

                markets = []
                async for api_event in client.get_all_events(
                    status="open",
                    limit=200,
                    max_pages=max_pages,
                    with_nested_markets=True,
                ):
                    if prefix_upper and not api_event.event_ticker.upper().startswith(prefix_upper):
                        continue

                    event_category = api_event.category
                    if no_sports and (
                        isinstance(event_category, str)
                        and event_category.strip().lower() == SPORTS_CATEGORY.lower()
                    ):
                        continue
                    if include_lower and (
                        not isinstance(event_category, str)
                        or event_category.strip().lower() != include_lower
                    ):
                        continue

                    markets.extend(api_event.markets or [])
            else:
                markets = [
                    m async for m in client.get_all_markets(status="open", max_pages=max_pages)
                ]

            if not markets:
                console.print("[yellow]No markets found matching category filters.[/yellow]")
                return

            from kalshi_research.analysis.scanner import MarketStatusVerifier

            scanner = MarketScanner(verifier=MarketStatusVerifier(exchange_status=exchange_status))
            results, title = _select_opportunity_results(
                scanner,
                markets,
                filter_type=filter_type,
                top_n=scan_top_n,
                min_volume=min_volume,
                max_spread=max_spread,
            )

            if not results:
                console.print("[yellow]No markets found matching criteria.[/yellow]")
                return

            liquidity_by_ticker: dict[str, int] = {}
            if show_liquidity or min_liquidity is not None:
                progress.add_task("Analyzing liquidity...", total=None)
                markets_by_ticker = {m.ticker: m for m in markets}
                liquidity_by_ticker = await _compute_liquidity_scores(
                    client,
                    markets_by_ticker,
                    results,
                    liquidity_depth=liquidity_depth,
                )

            if min_liquidity is not None:
                results = _filter_results_by_liquidity(
                    results,
                    liquidity_by_ticker,
                    min_liquidity=min_liquidity,
                    top_n=top_n,
                )

                if not results:
                    console.print("[yellow]No markets found matching liquidity threshold.[/yellow]")
                    return

    _render_opportunities_table(
        results,
        title,
        full=full,
        show_liquidity=show_liquidity,
        min_liquidity=min_liquidity,
        liquidity_by_ticker=liquidity_by_ticker,
    )


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
    category: Annotated[
        str | None,
        typer.Option(
            "--category",
            "-c",
            help="Filter by category (e.g., --category ai, --category Politics).",
        ),
    ] = None,
    no_sports: Annotated[
        bool,
        typer.Option("--no-sports", help="Exclude Sports category markets."),
    ] = False,
    event_prefix: Annotated[
        str | None,
        typer.Option("--event-prefix", help="Filter by event ticker prefix (e.g. KXFED)."),
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
    min_liquidity: Annotated[
        int | None,
        typer.Option(
            "--min-liquidity",
            help="Minimum liquidity score (0-100). Fetches orderbooks for candidate markets.",
        ),
    ] = None,
    show_liquidity: Annotated[
        bool,
        typer.Option(
            "--show-liquidity",
            help="Show liquidity score column (fetches orderbooks for displayed markets).",
        ),
    ] = False,
    liquidity_depth: Annotated[
        int,
        typer.Option(
            "--liquidity-depth",
            help="Orderbook depth levels for liquidity scoring.",
        ),
    ] = 25,
    full: Annotated[
        bool,
        typer.Option("--full", "-F", help="Show full tickers/titles without truncation."),
    ] = False,
) -> None:
    """Scan markets for opportunities."""
    asyncio.run(
        _scan_opportunities_async(
            filter_type=filter_type,
            category=category,
            no_sports=no_sports,
            event_prefix=event_prefix,
            full=full,
            top_n=top_n,
            min_volume=min_volume,
            max_spread=max_spread,
            max_pages=max_pages,
            min_liquidity=min_liquidity,
            show_liquidity=show_liquidity,
            liquidity_depth=liquidity_depth,
        )
    )


@app.command("arbitrage")
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
    asyncio.run(
        _scan_arbitrage_async(
            db_path=db_path,
            divergence_threshold=divergence_threshold,
            top_n=top_n,
            tickers_limit=tickers_limit,
            max_pages=max_pages,
            full=full,
        )
    )


async def _load_correlated_pairs(
    markets: list[Market],
    *,
    db_path: Path,
    tickers_limit: int,
) -> list[CorrelationResult]:
    if not db_path.exists():
        return []

    from kalshi_research.analysis.correlation import CorrelationAnalyzer
    from kalshi_research.data import DatabaseManager
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
        tickers_str = ", ".join(opp.tickers[:2])
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


async def _scan_arbitrage_async(
    *,
    db_path: Path,
    divergence_threshold: float,
    top_n: int,
    tickers_limit: int,
    max_pages: int | None,
    full: bool,
) -> None:
    from kalshi_research.analysis.correlation import ArbitrageOpportunity, CorrelationAnalyzer
    from kalshi_research.api import KalshiPublicClient

    if not db_path.exists():
        console.print(
            "[yellow]Warning:[/yellow] Database not found, analyzing current markets only"
        )

    async with KalshiPublicClient() as client:
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

    for m1, m2, deviation in analyzer.find_inverse_markets(markets, tolerance=divergence_threshold):
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

    opportunities.sort(key=lambda o: o.divergence, reverse=True)
    opportunities = opportunities[:top_n]

    _render_arbitrage_opportunities_table(opportunities, full=full)


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
    full: Annotated[
        bool,
        typer.Option("--full", "-F", help="Show full titles without truncation."),
    ] = False,
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
        movers: list[MoverRow] = []
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
        if full:
            table.add_column("Ticker", style="cyan", no_wrap=True)
            table.add_column("Title", style="white")
        else:
            table.add_column(
                "Ticker", style="cyan", no_wrap=True, overflow="ellipsis", max_width=35
            )
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

        from rich.console import Console

        output_console = console if not full else Console(width=200)
        output_console.print(table)
        output_console.print(f"\n[dim]Showing top {len(movers)} movers[/dim]")

    asyncio.run(_scan())
