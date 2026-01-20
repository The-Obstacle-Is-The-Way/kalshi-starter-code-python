"""Typer CLI commands for scanning markets and surfacing opportunities."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, TypedDict, cast

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from kalshi_research.cli.utils import console, exit_kalshi_api_error, run_async
from kalshi_research.paths import DEFAULT_DB_PATH

app = typer.Typer(help="Market scanning commands.")


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

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


class NewMarketRow(TypedDict):
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


class ScanProfile(str, Enum):
    """Opinionated presets for `kalshi scan opportunities`."""

    RAW = "raw"
    TRADEABLE = "tradeable"
    LIQUID = "liquid"
    EARLY = "early"


def _scan_profile_defaults(profile: ScanProfile) -> tuple[int, int, int | None]:
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


async def _fetch_opportunities_markets(
    client: KalshiPublicClient,
    *,
    category: str | None,
    no_sports: bool,
    event_prefix: str | None,
    max_pages: int | None,
) -> list[Market]:
    if not category and not no_sports and not event_prefix:
        return [m async for m in client.get_all_markets(status="open", max_pages=max_pages)]

    from kalshi_research.analysis.categories import SPORTS_CATEGORY, normalize_category

    include_category = normalize_category(category) if category else None
    include_lower = include_category.strip().lower() if include_category else None
    prefix_upper = event_prefix.upper() if event_prefix else None

    markets: list[Market] = []
    async for api_event in client.get_all_events(
        status="open",
        limit=200,
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


def _filter_markets_by_age(
    markets: list[Market],
    *,
    cutoff: datetime,
) -> tuple[list[Market], int]:
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


def _format_relative_age(*, now: datetime, timestamp: datetime) -> str:
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


def _parse_category_filter(category: str | None) -> set[str] | None:
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


def _is_unpriced_market(market: Market) -> bool:
    bid = market.yes_bid_cents
    ask = market.yes_ask_cents
    if bid is None or ask is None:
        return True
    return (bid == 0 and ask == 0) or (bid == 0 and ask == 100)


def _market_yes_price_display(market: Market) -> str:
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


def _validate_new_markets_args(*, hours: int, limit: int) -> None:
    """Validate `new-markets` CLI arguments and exit on invalid values."""
    if hours <= 0:
        console.print("[red]Error:[/red] --hours must be positive.")
        raise typer.Exit(1)
    if limit <= 0:
        console.print("[red]Error:[/red] --limit must be positive.")
        raise typer.Exit(1)


async def _iter_open_markets(
    client: KalshiPublicClient,
    *,
    max_pages: int | None,
    show_progress: bool,
) -> AsyncIterator[Market]:
    if not show_progress:
        async for market in client.get_all_markets(status="open", max_pages=max_pages):
            yield market
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Fetching markets...", total=None)
        async for market in client.get_all_markets(status="open", max_pages=max_pages):
            yield market


async def _collect_new_market_candidates(
    client: KalshiPublicClient,
    *,
    cutoff: datetime,
    include_unpriced: bool,
    max_pages: int | None,
    show_progress: bool,
) -> tuple[list[tuple[Market, datetime]], int, int]:
    candidates: list[tuple[Market, datetime]] = []
    missing_created_time = 0
    skipped_unpriced = 0

    async for market in _iter_open_markets(
        client,
        max_pages=max_pages,
        show_progress=show_progress,
    ):
        reference_time = market.created_time or market.open_time
        if reference_time < cutoff:
            continue

        if market.created_time is None:
            missing_created_time += 1

        if not include_unpriced and _is_unpriced_market(market):
            skipped_unpriced += 1
            continue

        candidates.append((market, reference_time))

    return candidates, missing_created_time, skipped_unpriced


async def _get_event_category(
    client: KalshiPublicClient,
    event_ticker: str,
    *,
    category_by_event: dict[str, str],
) -> str:
    cached = category_by_event.get(event_ticker)
    if cached is not None:
        return cached

    import httpx

    from kalshi_research.analysis.categories import classify_by_event_ticker
    from kalshi_research.api.exceptions import KalshiAPIError

    try:
        event = await client.get_event(event_ticker)
    except (KalshiAPIError, httpx.HTTPError):
        category = classify_by_event_ticker(event_ticker)
    else:
        if isinstance(event.category, str) and event.category.strip():
            category = event.category.strip()
        else:
            category = classify_by_event_ticker(event_ticker)

    category_by_event[event_ticker] = category
    return category


async def _build_new_markets_results(
    client: KalshiPublicClient,
    candidates: list[tuple[Market, datetime]],
    *,
    categories: set[str] | None,
    limit: int,
    now: datetime,
) -> tuple[list[NewMarketRow], int]:
    """Build table rows for the new-markets report.

    Args:
        client: Kalshi public API client used for event category lookups.
        candidates: Candidate markets paired with their "reference time" (created/open time).
        categories: Optional set of normalized categories to include.
        limit: Maximum number of rows to return.
        now: Reference clock used for relative age formatting.

    Returns:
        Tuple of (`rows`, `unpriced_included`) where `rows` is a list of table row dicts and
        `unpriced_included` counts unpriced markets included in the output.
    """
    results: list[NewMarketRow] = []
    category_by_event: dict[str, str] = {}
    unpriced_included = 0

    for market, reference_time in candidates:
        category = await _get_event_category(
            client,
            market.event_ticker,
            category_by_event=category_by_event,
        )
        if categories is not None and category.lower() not in categories:
            continue

        yes_display = _market_yes_price_display(market)
        if _is_unpriced_market(market):
            unpriced_included += 1

        results.append(
            {
                "ticker": market.ticker,
                "title": market.title,
                "event_ticker": market.event_ticker,
                "status": market.status.value,
                "yes_bid_cents": market.yes_bid_cents,
                "yes_ask_cents": market.yes_ask_cents,
                "yes_price_display": yes_display,
                "category": category,
                "created_time": reference_time.isoformat(),
                "age": _format_relative_age(now=now, timestamp=reference_time),
            }
        )

        if len(results) >= limit:
            break

    return results, unpriced_included


def _render_new_markets_table(
    results: list[NewMarketRow],
    *,
    hours: int,
    full: bool,
    skipped_unpriced: int,
    unpriced_included: int,
) -> None:
    from rich.console import Console

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
    """Fetch and sanity-check the exchange status response.

    Returns `None` when the status cannot be fetched or does not contain the expected boolean
    fields, allowing scans to proceed without exchange-halt checks.

    Args:
        client: Kalshi public API client.

    Returns:
        The raw status mapping when valid, otherwise `None`.
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
    from kalshi_research.analysis.scanner import MarketScanner
    from kalshi_research.cli.client_factory import public_client

    profile_min_volume, profile_max_spread, profile_min_liquidity = _scan_profile_defaults(profile)
    effective_min_volume = min_volume if min_volume is not None else profile_min_volume
    effective_max_spread = max_spread if max_spread is not None else profile_max_spread
    effective_min_liquidity = min_liquidity if min_liquidity is not None else profile_min_liquidity

    scan_top_n = top_n if effective_min_liquidity is None else min(top_n * 5, 50)

    async with public_client() as client:
        exchange_status = await _fetch_exchange_status(client)

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
                markets, missing_created_time = _filter_markets_by_age(markets, cutoff=cutoff)
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

            from kalshi_research.analysis.scanner import MarketStatusVerifier

            scanner = MarketScanner(verifier=MarketStatusVerifier(exchange_status=exchange_status))
            results, title = _select_opportunity_results(
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
                results = _filter_results_by_liquidity(
                    results,
                    liquidity_by_ticker,
                    min_liquidity=effective_min_liquidity,
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
        min_liquidity=effective_min_liquidity,
        liquidity_by_ticker=liquidity_by_ticker,
    )


@app.command("opportunities")
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


async def _scan_new_markets_async(
    *,
    hours: int,
    category: str | None,
    include_unpriced: bool,
    limit: int,
    max_pages: int | None,
    full: bool,
    output_json: bool,
) -> None:
    import json
    from datetime import UTC

    from kalshi_research.api.exceptions import KalshiAPIError
    from kalshi_research.cli.client_factory import public_client

    _validate_new_markets_args(hours=hours, limit=limit)
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=hours)
    categories = _parse_category_filter(category)

    missing_created_time = 0
    skipped_unpriced = 0
    unpriced_included = 0
    results: list[NewMarketRow] = []

    async with public_client() as client:
        try:
            (
                candidates,
                missing_created_time,
                skipped_unpriced,
            ) = await _collect_new_market_candidates(
                client,
                cutoff=cutoff,
                include_unpriced=include_unpriced,
                max_pages=max_pages,
                show_progress=not output_json,
            )
        except KalshiAPIError as exc:
            exit_kalshi_api_error(exc)
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from None

        candidates.sort(key=lambda item: item[1], reverse=True)
        results, unpriced_included = await _build_new_markets_results(
            client,
            candidates,
            categories=categories,
            limit=limit,
            now=now,
        )

    if not results and output_json:
        payload = {
            "hours": hours,
            "cutoff": cutoff.isoformat(),
            "count": 0,
            "markets": [],
            "missing_created_time": missing_created_time,
            "skipped_unpriced": skipped_unpriced,
        }
        typer.echo(json.dumps(payload, indent=2))
        return

    if not results and not output_json:
        console.print(f"[yellow]No new markets found in the last {hours} hours.[/yellow]")
        return

    if output_json:
        payload = {
            "hours": hours,
            "cutoff": cutoff.isoformat(),
            "count": len(results),
            "markets": results,
            "missing_created_time": missing_created_time,
            "skipped_unpriced": skipped_unpriced,
        }
        typer.echo(json.dumps(payload, indent=2))
        return

    if missing_created_time:
        console.print(
            "[yellow]Warning:[/yellow] "
            f"{missing_created_time} markets were missing created_time; using open_time as proxy."
        )

    _render_new_markets_table(
        results,
        hours=hours,
        full=full,
        skipped_unpriced=skipped_unpriced,
        unpriced_included=unpriced_included,
    )


@app.command("new-markets")
def scan_new_markets(
    hours: Annotated[
        int,
        typer.Option("--hours", help="Hours to look back for new markets (default: 24)."),
    ] = 24,
    category: Annotated[
        str | None,
        typer.Option(
            "--category",
            "--categories",
            "-c",
            help="Filter by category (comma-separated; e.g. --category politics,ai).",
        ),
    ] = None,
    include_unpriced: Annotated[
        bool,
        typer.Option(
            "--include-unpriced",
            help="Include markets without real price discovery (0/0 or 0/100 placeholder quotes).",
        ),
    ] = False,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum results to show."),
    ] = 20,
    max_pages: Annotated[
        int | None,
        typer.Option(
            "--max-pages",
            help="Optional pagination safety limit for market fetch (None = full).",
        ),
    ] = None,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
    full: Annotated[
        bool,
        typer.Option("--full", "-F", help="Show full tickers/titles without truncation."),
    ] = False,
) -> None:
    """Show markets created in the last N hours (information arbitrage window)."""
    run_async(
        _scan_new_markets_async(
            hours=hours,
            category=category,
            include_unpriced=include_unpriced,
            limit=limit,
            max_pages=max_pages,
            full=full,
            output_json=output_json,
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


async def _load_correlated_pairs(
    markets: list[Market],
    *,
    db_path: Path,
    tickers_limit: int,
) -> list[CorrelationResult]:
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


@app.command("movers")
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
