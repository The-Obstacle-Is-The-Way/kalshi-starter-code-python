"""Typer CLI commands for market lookup and exploration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer
from rich.table import Table

from kalshi_research.cli.utils import console, exit_kalshi_api_error, run_async

app = typer.Typer(help="Market lookup commands.")

if TYPE_CHECKING:
    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.api.models.market import Market


def _normalize_market_list_status(status: str | None) -> str | None:
    if status is None:
        return None

    from kalshi_research.api.models.market import MarketFilterStatus

    raw = status
    normalized = raw.strip().lower()

    # Common footgun: response status values differ from filter values.
    # Users often try "active" when they mean "open". Be helpful, but explicit.
    if normalized == "active":
        console.print(
            "[yellow]Warning:[/yellow] 'active' is a response status, not a valid filter. "
            "Using '--status open'."
        )
        return MarketFilterStatus.OPEN.value

    allowed = {s.value for s in MarketFilterStatus}
    if normalized not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        console.print(f"[red]Error:[/red] Invalid status filter '{raw}'.")
        console.print(f"[dim]Expected one of: {allowed_str}[/dim]")
        console.print(
            "[dim]Note: API responses may contain status values like 'active' or 'determined', "
            "but the /markets filter uses different values.[/dim]"
        )
        raise typer.Exit(2)

    return normalized


@app.command("get")
def market_get(
    ticker: Annotated[str, typer.Argument(help="Market ticker to fetch.")],
) -> None:
    """Fetch a single market by ticker."""
    from kalshi_research.api import KalshiPublicClient

    async def _get() -> None:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                market = await client.get_market(ticker)
            except KalshiAPIError as e:
                exit_kalshi_api_error(e)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        table = Table(title=f"Market: {market.ticker}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Title", market.title)
        table.add_row("Event", market.event_ticker)
        table.add_row("Status", market.status.value)
        yes_bid = market.yes_bid_cents
        yes_ask = market.yes_ask_cents
        no_bid = market.no_bid_cents
        no_ask = market.no_ask_cents
        yes_display = (
            f"{yes_bid}¢ / {yes_ask}¢" if yes_bid is not None and yes_ask is not None else "N/A"
        )
        no_display = (
            f"{no_bid}¢ / {no_ask}¢" if no_bid is not None and no_ask is not None else "N/A"
        )
        table.add_row("Yes Bid/Ask", yes_display)
        table.add_row("No Bid/Ask", no_display)
        table.add_row("Volume (24h)", f"{market.volume_24h:,}")
        table.add_row("Open Interest", f"{market.open_interest:,}")
        table.add_row("Open Time", market.open_time.isoformat())
        if market.created_time:
            table.add_row("Created Time", market.created_time.isoformat())
        table.add_row("Close Time", market.close_time.isoformat())

        console.print(table)

    run_async(_get())


@app.command("orderbook")
def market_orderbook(
    ticker: Annotated[str, typer.Argument(help="Market ticker to fetch orderbook for.")],
    depth: Annotated[int, typer.Option("--depth", "-d", help="Orderbook depth.")] = 5,
) -> None:
    """Fetch orderbook for a market."""
    from kalshi_research.api import KalshiPublicClient

    async def _orderbook() -> None:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                orderbook = await client.get_orderbook(ticker, depth=depth)
            except KalshiAPIError as e:
                exit_kalshi_api_error(e)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        table = Table(title=f"Orderbook: {ticker}")
        table.add_column("YES Bids", style="green")
        table.add_column("NO Bids", style="red")

        yes_bids = orderbook.yes_levels
        no_bids = orderbook.no_levels
        max_len = max(len(yes_bids), len(no_bids))

        for i in range(max_len):
            yes_str = f"{yes_bids[i][0]}¢ x {yes_bids[i][1]}" if i < len(yes_bids) else ""
            no_str = f"{no_bids[i][0]}¢ x {no_bids[i][1]}" if i < len(no_bids) else ""
            table.add_row(yes_str, no_str)

        console.print(table)

        if orderbook.spread is not None:
            console.print(f"\nSpread: {orderbook.spread}¢")
        if orderbook.midpoint is not None:
            console.print(f"Midpoint: {orderbook.midpoint:.1f}¢")

    run_async(_orderbook())


@app.command("liquidity")
def market_liquidity(
    ticker: Annotated[str, typer.Argument(help="Market ticker to analyze.")],
    depth: Annotated[
        int,
        typer.Option("--depth", "-d", help="Orderbook depth levels to fetch for analysis."),
    ] = 25,
    max_slippage_cents: Annotated[
        int,
        typer.Option("--max-slippage-cents", help="Max slippage (cents) for 'safe size'."),
    ] = 3,
) -> None:
    """Analyze market liquidity using orderbook depth and slippage estimates."""
    from kalshi_research.api import KalshiPublicClient

    async def _liquidity() -> None:
        from kalshi_research.analysis.liquidity import (
            estimate_slippage,
            liquidity_score,
            max_safe_order_size,
            suggest_execution_timing,
        )
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                market = await client.get_market(ticker)
                orderbook = await client.get_orderbook(ticker, depth=depth)
            except KalshiAPIError as e:
                exit_kalshi_api_error(e)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        analysis = liquidity_score(market, orderbook)
        safe_yes = max_safe_order_size(orderbook, "yes", max_slippage_cents=max_slippage_cents)
        safe_no = max_safe_order_size(orderbook, "no", max_slippage_cents=max_slippage_cents)
        timing = suggest_execution_timing()

        summary = Table(title=f"Liquidity Analysis: {ticker}")
        summary.add_column("Metric", style="cyan")
        summary.add_column("Value", style="green")

        spread = orderbook.spread
        summary.add_row("Score", f"{analysis.score}/100 ({analysis.grade.value.upper()})")
        summary.add_row("Spread", f"{spread}¢" if spread is not None else "N/A")
        summary.add_row(
            "Depth (±10c)",
            f"{analysis.depth.total_contracts:,} contracts "
            f"(YES {analysis.depth.yes_side_depth:,} / NO {analysis.depth.no_side_depth:,})",
        )
        summary.add_row("Imbalance", f"{analysis.depth.imbalance_ratio:+.1%}")
        summary.add_row("Volume (24h)", f"{market.volume_24h:,}")
        summary.add_row("Open Interest", f"{market.open_interest:,}")
        summary.add_row(
            f"Max Safe Size (≤{max_slippage_cents}c)",
            f"Buy YES: {safe_yes:,} | Buy NO: {safe_no:,}",
        )

        console.print(summary)

        slippage_table = Table(title="Order Size Analysis (Buy YES)")
        slippage_table.add_column("Qty", justify="right", style="cyan")
        slippage_table.add_column("Slippage", style="yellow")
        slippage_table.add_column("Avg Fill", style="green")
        slippage_table.add_column("Fillable", justify="right", style="magenta")
        slippage_table.add_column("Levels", justify="right", style="dim")

        for qty in [10, 50, 100, 250, 500]:
            slip = estimate_slippage(orderbook, "yes", "buy", qty)
            fillable = (
                f"{slip.fillable_quantity:,}"
                if slip.remaining_unfilled == 0
                else f"{slip.fillable_quantity:,} (rem {slip.remaining_unfilled:,})"
            )
            avg_fill = f"{slip.avg_fill_price:.1f}¢" if slip.fillable_quantity > 0 else "N/A"
            slippage_table.add_row(
                f"{qty:,}",
                f"{slip.slippage_cents:.1f}¢ ({slip.slippage_pct:.1f}%)",
                avg_fill,
                fillable,
                f"{slip.levels_crossed}",
            )

        console.print(slippage_table)

        optimal = (
            f"{timing.optimal_hours_utc[0]}:00-{timing.optimal_hours_utc[-1]}:00 UTC"
            if timing.optimal_hours_utc
            else "N/A"
        )
        avoid = (
            f"{timing.avoid_hours_utc[0]}:00-{timing.avoid_hours_utc[-1]}:00 UTC"
            if timing.avoid_hours_utc
            else "N/A"
        )
        console.print(
            "\nExecution Timing:",
            f"[green]optimal[/green] {optimal}, [yellow]avoid[/yellow] {avoid}",
        )

        if analysis.warnings:
            console.print("\n[yellow]Warnings:[/yellow]")
            for w in analysis.warnings:
                console.print(f"- {w}")

    run_async(_liquidity())


@app.command("history")
def market_history(
    ticker: Annotated[str, typer.Argument(help="Market ticker to fetch candlesticks for.")],
    series_ticker: Annotated[
        str | None,
        typer.Option(
            "--series",
            help="Optional series ticker (uses series candlesticks endpoint).",
        ),
    ] = None,
    interval: Annotated[
        str,
        typer.Option("--interval", "-i", help="Candle interval: 1m, 1h, 1d."),
    ] = "1h",
    days: Annotated[
        int,
        typer.Option("--days", help="Lookback window in days (used when --start-ts is not set)."),
    ] = 7,
    start_ts: Annotated[
        int | None,
        typer.Option("--start-ts", help="Start timestamp (Unix seconds)."),
    ] = None,
    end_ts: Annotated[
        int | None,
        typer.Option("--end-ts", help="End timestamp (Unix seconds). Defaults to now."),
    ] = None,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Fetch candlestick history for a market."""
    import json
    from datetime import UTC, datetime

    from kalshi_research.api import KalshiPublicClient

    interval_map = {"1m": 1, "1h": 60, "1d": 1440}
    if interval not in interval_map:
        allowed = ", ".join(sorted(interval_map))
        console.print(
            f"[red]Error:[/red] Invalid interval '{interval}'. Expected one of: {allowed}"
        )
        raise typer.Exit(2)

    if end_ts is None:
        end_ts = int(datetime.now(UTC).timestamp())
    if start_ts is None:
        if days <= 0:
            console.print("[red]Error:[/red] --days must be > 0 when --start-ts is not set.")
            raise typer.Exit(2)
        start_ts = end_ts - days * 24 * 60 * 60

    if start_ts >= end_ts:
        console.print("[red]Error:[/red] start-ts must be < end-ts.")
        raise typer.Exit(2)

    async def _history() -> None:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                if series_ticker is not None:
                    candles = await client.get_series_candlesticks(
                        series_ticker=series_ticker,
                        ticker=ticker,
                        start_ts=start_ts,
                        end_ts=end_ts,
                        period_interval=interval_map[interval],
                    )
                else:
                    responses = await client.get_candlesticks(
                        market_tickers=[ticker],
                        start_ts=start_ts,
                        end_ts=end_ts,
                        period_interval=interval_map[interval],
                    )
                    candles = responses[0].candlesticks if responses else []
            except KalshiAPIError as e:
                exit_kalshi_api_error(e)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        if not candles:
            console.print("[yellow]No candlesticks returned for the given window.[/yellow]")
            return

        if output_json:
            payload = [c.model_dump(mode="json") for c in candles]
            typer.echo(json.dumps(payload, indent=2, default=str))
            return

        table = Table(title=f"Candlestick History: {ticker}")
        table.add_column("Period End (UTC)", style="cyan", no_wrap=True)
        table.add_column("Close", justify="right", style="green")
        table.add_column("Volume", justify="right", style="magenta")
        table.add_column("OI", justify="right", style="yellow")

        for candle in candles[-50:]:
            close_price = candle.price.close
            close_str = f"{close_price}¢" if close_price is not None else "N/A"
            table.add_row(
                candle.period_end.isoformat(),
                close_str,
                f"{candle.volume:,}",
                f"{candle.open_interest:,}",
            )

        console.print(table)

    run_async(_history())


def _optional_lower(raw: str | None) -> str | None:
    if raw is None:
        return None
    stripped = raw.strip()
    return stripped.lower() if stripped else None


async def _fetch_markets_for_market_list_from_events(
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
    markets: list[Market] = []
    async for api_event in client.get_all_events(
        status=status_filter,
        limit=200,
        with_nested_markets=True,
    ):
        if prefix_upper and not api_event.event_ticker.upper().startswith(prefix_upper):
            continue

        event_category_lower = _optional_lower(api_event.category)
        if include_category_lower is not None and event_category_lower != include_category_lower:
            continue
        if exclude_category_lower is not None and event_category_lower == exclude_category_lower:
            continue

        for market in api_event.markets or []:
            markets.append(market)
            if len(markets) >= limit:
                return markets

    return markets


def _filter_markets_for_market_list_by_event_ticker(
    markets: list[Market],
    *,
    include_category: str | None,
    exclude_category: str | None,
    prefix_upper: str | None,
) -> list[Market]:
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


def _render_market_list_table(
    markets: list[Market],
    *,
    status_filter: str | None,
    limit: int,
    full: bool,
) -> None:
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


async def _market_list_async(
    *,
    status: str | None,
    event: str | None,
    category: str | None,
    exclude_category: str | None,
    event_prefix: str | None,
    limit: int,
    full: bool,
) -> None:
    from kalshi_research.analysis.categories import normalize_category
    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.api.exceptions import KalshiAPIError

    status_filter = _normalize_market_list_status(status)

    include_category = normalize_category(category) if category else None
    exclude_normalized = normalize_category(exclude_category) if exclude_category else None
    include_category_lower = _optional_lower(include_category)
    exclude_category_lower = _optional_lower(exclude_normalized)
    prefix_upper = event_prefix.upper() if event_prefix else None

    can_use_events = status_filter in {None, "open", "closed", "settled"}
    use_events = can_use_events and event is None and (category or exclude_category or event_prefix)

    try:
        async with KalshiPublicClient() as client:
            if use_events:
                markets = await _fetch_markets_for_market_list_from_events(
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
                    markets = _filter_markets_for_market_list_by_event_ticker(
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

    _render_market_list_table(
        markets,
        status_filter=status_filter,
        limit=limit,
        full=full,
    )


@app.command("list")
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
        _market_list_async(
            status=status,
            event=event,
            category=category,
            exclude_category=exclude_category,
            event_prefix=event_prefix,
            limit=limit,
            full=full,
        )
    )


@app.command("search")
def market_search(
    query: Annotated[
        str, typer.Argument(help="Search query (keywords to match in title/subtitle).")
    ],
    db: Annotated[
        str,
        typer.Option("--db", help="Path to database file."),
    ] = "data/kalshi.db",
    status: Annotated[
        str | None,
        typer.Option(
            "--status",
            "-s",
            help="Filter by market status (e.g., open, closed, settled).",
        ),
    ] = "open",
    category: Annotated[
        str | None,
        typer.Option(
            "--category",
            "-c",
            help="Filter by category (substring match, case-insensitive).",
        ),
    ] = None,
    event: Annotated[
        str | None,
        typer.Option("--event", "-e", help="Filter by exact event ticker."),
    ] = None,
    series: Annotated[
        str | None,
        typer.Option("--series", help="Filter by exact series ticker."),
    ] = None,
    min_volume: Annotated[
        int | None,
        typer.Option("--min-volume", help="Minimum 24h volume (requires price snapshot)."),
    ] = None,
    max_spread: Annotated[
        int | None,
        typer.Option("--max-spread", help="Maximum spread in cents (requires price snapshot)."),
    ] = None,
    top: Annotated[
        int,
        typer.Option("--top", "-n", help="Maximum number of results to return."),
    ] = 20,
    format_output: Annotated[
        str,
        typer.Option("--format", help="Output format: table or json."),
    ] = "table",
) -> None:
    """Search markets in the local database by keyword.

    Uses FTS5 full-text search if available, otherwise falls back to LIKE queries.
    Searches are performed on the local database, not the live API.

    Run 'kalshi data sync-markets' first to populate/update the database.
    """
    run_async(
        _market_search_async(
            query=query,
            db=db,
            status=status,
            category=category,
            event=event,
            series=series,
            min_volume=min_volume,
            max_spread=max_spread,
            top=top,
            format_output=format_output,
        )
    )


async def _market_search_async(
    *,
    query: str,
    db: str,
    status: str | None,
    category: str | None,
    event: str | None,
    series: str | None,
    min_volume: int | None,
    max_spread: int | None,
    top: int,
    format_output: str,
) -> None:
    """Async implementation of market search."""
    import json
    from pathlib import Path

    from kalshi_research.data.database import DatabaseManager
    from kalshi_research.data.repositories.search import SearchRepository
    from kalshi_research.data.search_utils import has_fts5_support

    db_path = Path(db)
    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database file not found: {db}")
        console.print(
            "[dim]Run 'kalshi data init' to create the database, "
            "then 'kalshi data sync-markets' to populate it.[/dim]"
        )
        raise typer.Exit(1)

    db_manager = DatabaseManager(str(db_path))
    session = await db_manager.get_session()

    try:
        # Check FTS5 support and warn if unavailable
        has_fts5 = await has_fts5_support(session)
        if not has_fts5:
            console.print(
                "[yellow]Warning:[/yellow] FTS5 not available. Using slower LIKE-based search."
            )

        search_repo = SearchRepository(session)
        results = await search_repo.search_markets(
            query,
            status=status,
            category=category,
            event_ticker=event,
            series_ticker=series,
            min_volume=min_volume,
            max_spread=max_spread,
            limit=top,
        )
    finally:
        await session.close()
        await db_manager.close()

    if not results:
        console.print("[yellow]No markets found.[/yellow]")
        return

    if format_output == "json":
        # Output as JSON
        json_results = [
            {
                "ticker": r.ticker,
                "title": r.title,
                "subtitle": r.subtitle,
                "event_ticker": r.event_ticker,
                "event_category": r.event_category,
                "status": r.status,
                "midpoint": r.midpoint,
                "spread": r.spread,
                "volume_24h": r.volume_24h,
                "close_time": r.close_time.isoformat(),
                "expiration_time": r.expiration_time.isoformat(),
            }
            for r in results
        ]
        typer.echo(json.dumps(json_results, indent=2))
    else:
        # Output as table
        table = Table(title=f"Search Results: '{query}' ({len(results)} found)")
        table.add_column("Ticker", style="cyan", no_wrap=True)
        table.add_column("Title", style="white")
        table.add_column("Category", style="magenta")
        table.add_column("Status", style="yellow")
        table.add_column("Mid%", justify="right", style="green")
        table.add_column("Spread", justify="right", style="dim")
        table.add_column("Vol24h", justify="right", style="blue")

        for result in results:
            mid_display = f"{result.midpoint:.1f}" if result.midpoint is not None else "—"
            spread_display = f"{result.spread}¢" if result.spread is not None else "—"
            vol_display = f"{result.volume_24h:,}" if result.volume_24h is not None else "—"

            table.add_row(
                result.ticker,
                result.title[:60] + "..." if len(result.title) > 60 else result.title,
                result.event_category or "—",
                result.status,
                mid_display,
                spread_display,
                vol_display,
            )

        console.print(table)
