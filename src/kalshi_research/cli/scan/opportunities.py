"""Typer CLI command for market opportunity scanning."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Annotated

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

from kalshi_research.cli.scan._opportunities_helpers import (
    ScanProfile,
    fetch_exchange_status,
    filter_markets_by_age,
    filter_results_by_liquidity,
    render_opportunities_table,
    scan_profile_defaults,
    select_opportunity_results,
)
from kalshi_research.cli.utils import console, run_async
from kalshi_research.constants import DEFAULT_PAGINATION_LIMIT

if TYPE_CHECKING:
    from kalshi_research.analysis.scanner import ScanResult
    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.api.models.market import Market

# Re-export helpers with underscore prefix for backwards compatibility
_scan_profile_defaults = scan_profile_defaults
_select_opportunity_results = select_opportunity_results
_filter_results_by_liquidity = filter_results_by_liquidity
_render_opportunities_table = render_opportunities_table
_fetch_exchange_status = fetch_exchange_status
_filter_markets_by_age = filter_markets_by_age


async def _fetch_opportunities_markets(
    client: KalshiPublicClient,
    *,
    category: str | None,
    no_sports: bool,
    event_prefix: str | None,
    max_pages: int | None,
) -> list[Market]:
    """Fetch markets for opportunity scanning, applying category/event filters."""
    if not category and not no_sports and not event_prefix:
        return [m async for m in client.get_all_markets(status="open", max_pages=max_pages)]

    from kalshi_research.analysis.categories import SPORTS_CATEGORY, normalize_category

    include_category = normalize_category(category) if category else None
    include_lower = include_category.strip().lower() if include_category else None
    prefix_upper = event_prefix.upper() if event_prefix else None

    markets: list[Market] = []
    async for api_event in client.get_all_events(
        status="open",
        limit=DEFAULT_PAGINATION_LIMIT,
        max_pages=max_pages,
        with_nested_markets=True,
    ):
        if prefix_upper and not api_event.event_ticker.upper().startswith(prefix_upper):
            continue

        event_category = api_event.category
        if (
            no_sports
            and isinstance(event_category, str)
            and event_category.strip().lower() == SPORTS_CATEGORY.lower()
        ):
            continue

        if include_lower and (
            not isinstance(event_category, str) or event_category.strip().lower() != include_lower
        ):
            continue

        markets.extend(api_event.markets or [])

    return markets


async def _compute_liquidity_scores(
    client: KalshiPublicClient,
    markets_by_ticker: dict[str, Market],
    results: list[ScanResult],
    *,
    liquidity_depth: int,
) -> dict[str, int]:
    """Compute liquidity scores for scan results."""
    import httpx

    from kalshi_research.analysis.liquidity import liquidity_score
    from kalshi_research.api.exceptions import KalshiAPIError

    scores: dict[str, int] = {}

    for r in results:
        market = markets_by_ticker.get(r.ticker)
        if market is None:
            continue
        try:
            orderbook = await client.get_orderbook(r.ticker, depth=liquidity_depth)
        except (KalshiAPIError, httpx.HTTPError) as e:
            console.print(f"[yellow]Warning:[/yellow] Skipping liquidity for {r.ticker}: {e}")
            continue

        scores[r.ticker] = liquidity_score(market, orderbook).score

    return scores


async def _scan_opportunities_async(
    *,
    profile: ScanProfile,
    filter_type: str | None,
    category: str | None,
    no_sports: bool,
    event_prefix: str | None,
    full: bool,
    top_n: int,
    min_volume: int | None,
    max_spread: int | None,
    early_hours: int,
    max_pages: int | None,
    min_liquidity: int | None,
    show_liquidity: bool,
    liquidity_depth: int,
) -> None:
    """Async implementation of scan_opportunities."""
    from kalshi_research.analysis.scanner import MarketScanner, MarketStatusVerifier
    from kalshi_research.cli.client_factory import public_client

    profile_min_volume, profile_max_spread, profile_min_liquidity = scan_profile_defaults(profile)
    effective_min_volume = min_volume if min_volume is not None else profile_min_volume
    effective_max_spread = max_spread if max_spread is not None else profile_max_spread
    effective_min_liquidity = min_liquidity if min_liquidity is not None else profile_min_liquidity

    scan_top_n = top_n if effective_min_liquidity is None else min(top_n * 5, 50)

    async with public_client() as client:
        exchange_status = await fetch_exchange_status(client)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Fetching markets...", total=None)
            markets = await _fetch_opportunities_markets(
                client,
                category=category,
                no_sports=no_sports,
                event_prefix=event_prefix,
                max_pages=max_pages,
            )

            if not markets:
                console.print("[yellow]No markets found matching category filters.[/yellow]")
                return

            if profile is ScanProfile.EARLY:
                from datetime import UTC

                if early_hours <= 0:
                    console.print("[red]Error:[/red] --early-hours must be positive.")
                    raise typer.Exit(1)

                now = datetime.now(UTC)
                cutoff = now - timedelta(hours=early_hours)
                markets, missing_created_time = filter_markets_by_age(markets, cutoff=cutoff)
                if not markets:
                    console.print(
                        f"[yellow]No markets found in the last {early_hours} hours.[/yellow]"
                    )
                    return
                if missing_created_time:
                    console.print(
                        "[yellow]Warning:[/yellow] Some markets are missing created_time; "
                        "approximating newness with open_time."
                    )

            scanner = MarketScanner(verifier=MarketStatusVerifier(exchange_status=exchange_status))
            results, title = select_opportunity_results(
                scanner,
                markets,
                filter_type=filter_type,
                top_n=scan_top_n,
                min_volume=effective_min_volume,
                max_spread=effective_max_spread,
            )

            if not results:
                console.print("[yellow]No markets found matching criteria.[/yellow]")
                return

            liquidity_by_ticker: dict[str, int] = {}
            if show_liquidity or effective_min_liquidity is not None:
                progress.add_task("Analyzing liquidity...", total=None)
                markets_by_ticker = {m.ticker: m for m in markets}
                liquidity_by_ticker = await _compute_liquidity_scores(
                    client,
                    markets_by_ticker,
                    results,
                    liquidity_depth=liquidity_depth,
                )

            if effective_min_liquidity is not None:
                results = filter_results_by_liquidity(
                    results,
                    liquidity_by_ticker,
                    min_liquidity=effective_min_liquidity,
                    top_n=top_n,
                )

                if not results:
                    console.print("[yellow]No markets found matching liquidity threshold.[/yellow]")
                    return

    render_opportunities_table(
        results,
        title,
        full=full,
        show_liquidity=show_liquidity,
        min_liquidity=effective_min_liquidity,
        liquidity_by_ticker=liquidity_by_ticker,
    )


def scan_opportunities(
    profile: Annotated[
        ScanProfile,
        typer.Option(
            "--profile",
            help="Quality profile preset for `scan opportunities` (raw, tradeable, liquid, early).",
        ),
    ] = ScanProfile.RAW,
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
        int | None,
        typer.Option(
            "--min-volume",
            help="Minimum 24h volume (close-race filter only). Overrides --profile default.",
        ),
    ] = None,
    max_spread: Annotated[
        int | None,
        typer.Option(
            "--max-spread",
            help=(
                "Maximum bid-ask spread in cents (close-race filter only). "
                "Overrides --profile default."
            ),
        ),
    ] = None,
    early_hours: Annotated[
        int,
        typer.Option(
            "--early-hours",
            help=(
                "When --profile early, only consider markets created/opened within this many hours."
            ),
        ),
    ] = 72,
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
    run_async(
        _scan_opportunities_async(
            profile=profile,
            filter_type=filter_type,
            category=category,
            no_sports=no_sports,
            event_prefix=event_prefix,
            full=full,
            top_n=top_n,
            min_volume=min_volume,
            max_spread=max_spread,
            early_hours=early_hours,
            max_pages=max_pages,
            min_liquidity=min_liquidity,
            show_liquidity=show_liquidity,
            liquidity_depth=liquidity_depth,
        )
    )
