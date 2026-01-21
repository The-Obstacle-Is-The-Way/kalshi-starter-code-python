"""Market list command - list markets with optional filters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer
from rich.table import Table

from kalshi_research.cli.market._helpers import normalize_market_list_status, optional_lower
from kalshi_research.cli.utils import console, exit_kalshi_api_error, run_async
from kalshi_research.constants import DEFAULT_PAGINATION_LIMIT

if TYPE_CHECKING:
    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.api.models.market import Market


async def fetch_markets_from_events(
    client: KalshiPublicClient,
    *,
    status_filter: str | None,
    include_category_lower: str | None,
    exclude_category_lower: str | None,
    prefix_upper: str | None,
    limit: int,
) -> list[Market]:
    """Fetch markets by iterating events with nested markets (SSOT for categories).

    Args:
        client: Kalshi public API client.
        status_filter: Optional event status filter for `/events`.
        include_category_lower: Optional lowercase event category to include.
        exclude_category_lower: Optional lowercase event category to exclude.
        prefix_upper: Optional event ticker prefix filter (uppercase).
        limit: Maximum number of markets to return.

    Returns:
        A list of markets collected from events, truncated to `limit`.
    """
    if limit <= 0:
        return []

    markets: list[Market] = []
    async for api_event in client.get_all_events(
        status=status_filter,
        limit=DEFAULT_PAGINATION_LIMIT,
        with_nested_markets=True,
    ):
        if prefix_upper and not api_event.event_ticker.upper().startswith(prefix_upper):
            continue

        event_category_lower = optional_lower(api_event.category)
        if include_category_lower is not None and event_category_lower != include_category_lower:
            continue
        if exclude_category_lower is not None and event_category_lower == exclude_category_lower:
            continue

        for market in api_event.markets or []:
            markets.append(market)
            if len(markets) >= limit:
                return markets

    return markets


def filter_markets_by_event_ticker(
    markets: list[Market],
    *,
    include_category: str | None,
    exclude_category: str | None,
    prefix_upper: str | None,
) -> list[Market]:
    """Filter markets by category or event ticker prefix.

    Args:
        markets: List of markets to filter.
        include_category: Optional category to include.
        exclude_category: Optional category to exclude.
        prefix_upper: Optional event ticker prefix filter (uppercase).

    Returns:
        Filtered list of markets.
    """
    from kalshi_research.analysis.categories import classify_by_event_ticker

    filtered: list[Market] = []
    for market in markets:
        if prefix_upper and not market.event_ticker.upper().startswith(prefix_upper):
            continue

        derived_category = classify_by_event_ticker(market.event_ticker)
        if include_category and derived_category != include_category:
            continue
        if exclude_category and derived_category == exclude_category:
            continue
        filtered.append(market)

    return filtered


def render_market_list_table(
    markets: list[Market],
    *,
    status_filter: str | None,
    limit: int,
    full: bool,
) -> None:
    """Render markets as a table.

    Args:
        markets: List of markets to display.
        status_filter: Status filter used (for title display).
        limit: Maximum number of markets to display.
        full: If True, show full tickers/titles without truncation.
    """
    from rich.console import Console

    table = Table(title=f"Markets (status={status_filter or 'all'})")
    table.add_column("Ticker", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Status", style="dim")
    table.add_column("Yes Bid", style="green", justify="right")
    table.add_column("Volume", justify="right")

    for market in markets[:limit]:
        ticker = market.ticker if full else market.ticker[:30]
        title = (
            market.title if full else market.title[:40] + ("..." if len(market.title) > 40 else "")
        )
        yes_bid = market.yes_bid_cents
        table.add_row(
            ticker,
            title,
            market.status.value,
            f"{yes_bid}¢" if yes_bid is not None else "N/A",
            f"{market.volume_24h:,}",
        )

    output_console = console if not full else Console(width=200)
    output_console.print(table)

    displayed, available = min(len(markets), limit), len(markets)
    suffix = f" of {available}" if available > limit else ""
    output_console.print(f"\n[dim]Showing {displayed}{suffix} markets[/dim]")


async def market_list_async(
    *,
    status: str | None,
    event: str | None,
    category: str | None,
    exclude_category: str | None,
    event_prefix: str | None,
    limit: int,
    full: bool,
) -> None:
    """Async implementation of market list command."""
    from kalshi_research.analysis.categories import normalize_category
    from kalshi_research.api.exceptions import KalshiAPIError
    from kalshi_research.cli.client_factory import public_client

    status_filter = normalize_market_list_status(status)

    include_category = normalize_category(category) if category else None
    exclude_normalized = normalize_category(exclude_category) if exclude_category else None
    include_category_lower = optional_lower(include_category)
    exclude_category_lower = optional_lower(exclude_normalized)
    prefix_upper = event_prefix.upper() if event_prefix else None

    can_use_events = status_filter in {None, "open", "closed", "settled"}
    use_events = can_use_events and event is None and (category or exclude_category or event_prefix)

    try:
        async with public_client() as client:
            if use_events:
                markets = await fetch_markets_from_events(
                    client,
                    status_filter=status_filter,
                    include_category_lower=include_category_lower,
                    exclude_category_lower=exclude_category_lower,
                    prefix_upper=prefix_upper,
                    limit=limit,
                )
            else:
                request_limit = limit
                if event is None and (category or exclude_category or event_prefix):
                    request_limit = max(limit, 1000)
                markets = await client.get_markets(
                    status=status_filter,
                    event_ticker=event,
                    limit=request_limit,
                )

                if category or exclude_category or event_prefix:
                    markets = filter_markets_by_event_ticker(
                        markets,
                        include_category=include_category,
                        exclude_category=exclude_normalized,
                        prefix_upper=prefix_upper,
                    )
    except KalshiAPIError as exc:
        exit_kalshi_api_error(exc)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None

    if not markets:
        console.print("[yellow]No markets found.[/yellow]")
        return

    render_market_list_table(
        markets,
        status_filter=status_filter,
        limit=limit,
        full=full,
    )


def market_list(
    status: Annotated[
        str | None,
        typer.Option(
            "--status",
            "-s",
            help=(
                "Filter by status: unopened, open, paused, closed, settled "
                "(filter values, not response statuses)."
            ),
        ),
    ] = "open",
    event: Annotated[
        str | None,
        typer.Option("--event", "-e", help="Filter by event ticker."),
    ] = None,
    category: Annotated[
        str | None,
        typer.Option(
            "--category",
            "-c",
            help=(
                "Filter by category (e.g. Politics, Economics, 'Science and Technology'). "
                "Aliases: pol, econ, tech, ai, crypto, climate."
            ),
        ),
    ] = None,
    exclude_category: Annotated[
        str | None,
        typer.Option(
            "--exclude-category",
            "-X",
            help="Exclude a category (e.g. --exclude-category Sports).",
        ),
    ] = None,
    event_prefix: Annotated[
        str | None,
        typer.Option("--event-prefix", help="Filter by event ticker prefix (e.g. KXFED)."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum number of results."),
    ] = 20,
    full: Annotated[
        bool,
        typer.Option("--full", "-F", help="Show full tickers/titles without truncation."),
    ] = False,
) -> None:
    """List markets with optional filters."""
    run_async(
        market_list_async(
            status=status,
            event=event,
            category=category,
            exclude_category=exclude_category,
            event_prefix=event_prefix,
            limit=limit,
            full=full,
        )
    )
