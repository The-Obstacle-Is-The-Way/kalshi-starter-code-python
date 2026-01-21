"""Typer CLI command for new market discovery."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Annotated

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

from kalshi_research.cli.scan._helpers import (
    NewMarketRow,
    format_relative_age,
    is_unpriced_market,
    market_yes_price_display,
    parse_category_filter,
    render_new_markets_table,
    validate_new_markets_args,
)
from kalshi_research.cli.utils import console, exit_kalshi_api_error, run_async

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.api.models.market import Market

# Re-export helpers with underscore prefix for backwards compatibility
_format_relative_age = format_relative_age
_parse_category_filter = parse_category_filter
_is_unpriced_market = is_unpriced_market
_market_yes_price_display = market_yes_price_display
_validate_new_markets_args = validate_new_markets_args
_render_new_markets_table = render_new_markets_table


async def _iter_open_markets(
    client: KalshiPublicClient,
    *,
    max_pages: int | None,
    show_progress: bool,
) -> AsyncIterator[Market]:
    """Iterate over open markets, optionally showing a progress spinner."""
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
    """Collect candidate markets created after cutoff.

    Returns:
        Tuple of (candidates, missing_created_time_count, skipped_unpriced_count).
    """
    candidates: list[tuple[Market, datetime]] = []
    missing_created_time = 0
    skipped_unpriced = 0

    async for market in _iter_open_markets(
        client,
        max_pages=max_pages,
        show_progress=show_progress,
    ):
        reference_time = market.created_time or market.open_time
        if reference_time is None:
            missing_created_time += 1
            continue
        if reference_time < cutoff:
            continue

        if market.created_time is None:
            missing_created_time += 1

        if not include_unpriced and is_unpriced_market(market):
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
    """Get the category for an event, using cache and falling back to classification."""
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

        yes_display = market_yes_price_display(market)
        if is_unpriced_market(market):
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
                "age": format_relative_age(now=now, timestamp=reference_time),
            }
        )

        if len(results) >= limit:
            break

    return results, unpriced_included


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
    """Async implementation of scan_new_markets."""
    import json
    from datetime import UTC

    from kalshi_research.api.exceptions import KalshiAPIError
    from kalshi_research.cli.client_factory import public_client

    validate_new_markets_args(hours=hours, limit=limit)
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=hours)
    categories = parse_category_filter(category)

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

    render_new_markets_table(
        results,
        hours=hours,
        full=full,
        skipped_unpriced=skipped_unpriced,
        unpriced_included=unpriced_included,
    )


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
