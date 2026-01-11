import asyncio
from typing import Annotated

import typer
from rich.table import Table

from kalshi_research.cli.utils import console

app = typer.Typer(help="Market lookup commands.")


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
                console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
                raise typer.Exit(1) from None
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        table = Table(title=f"Market: {market.ticker}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Title", market.title)
        table.add_row("Event", market.event_ticker)
        table.add_row("Status", market.status.value)
        table.add_row("Yes Bid/Ask", f"{market.yes_bid_cents}¢ / {market.yes_ask_cents}¢")
        table.add_row("No Bid/Ask", f"{market.no_bid_cents}¢ / {market.no_ask_cents}¢")
        table.add_row("Volume (24h)", f"{market.volume_24h:,}")
        table.add_row("Open Interest", f"{market.open_interest:,}")
        table.add_row("Open Time", market.open_time.isoformat())
        if market.created_time:
            table.add_row("Created Time", market.created_time.isoformat())
        table.add_row("Close Time", market.close_time.isoformat())

        console.print(table)

    asyncio.run(_get())


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
                console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
                raise typer.Exit(1) from None
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

    asyncio.run(_orderbook())


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
                console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
                raise typer.Exit(1) from None
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

    asyncio.run(_liquidity())


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
                console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
                raise typer.Exit(1) from None
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        if not candles:
            console.print("[yellow]No candlesticks returned for the given window.[/yellow]")
            return

        if output_json:
            payload = [c.model_dump(mode="json") for c in candles]
            console.print(json.dumps(payload, indent=2, default=str))
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

    asyncio.run(_history())


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
    from kalshi_research.api import KalshiPublicClient

    async def _list() -> None:
        from kalshi_research.api.exceptions import KalshiAPIError

        status_filter = _normalize_market_list_status(status)

        try:
            async with KalshiPublicClient() as client:
                request_limit = limit
                if event is None and (category or exclude_category or event_prefix):
                    request_limit = max(limit, 1000)
                markets = await client.get_markets(
                    status=status_filter,
                    event_ticker=event,
                    limit=request_limit,
                )
        except KalshiAPIError as e:
            console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
            raise typer.Exit(1) from None
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

        if category or exclude_category or event_prefix:
            from kalshi_research.analysis.categories import (
                classify_by_event_ticker,
                normalize_category,
            )

            include_category = normalize_category(category) if category else None
            exclude_normalized = normalize_category(exclude_category) if exclude_category else None
            prefix_upper = event_prefix.upper() if event_prefix else None

            filtered = []
            for market in markets:
                if prefix_upper and not market.event_ticker.upper().startswith(prefix_upper):
                    continue

                derived_category = classify_by_event_ticker(market.event_ticker)
                if include_category and derived_category != include_category:
                    continue
                if exclude_normalized and derived_category == exclude_normalized:
                    continue
                filtered.append(market)

            markets = filtered

        if not markets:
            console.print("[yellow]No markets found.[/yellow]")
            return

        table = Table(title=f"Markets (status={status_filter or 'all'})")
        table.add_column("Ticker", style="cyan", no_wrap=True)
        table.add_column("Title", style="white")
        table.add_column("Status", style="dim")
        table.add_column("Yes Bid", style="green", justify="right")
        table.add_column("Volume", justify="right")

        for m in markets[:limit]:
            ticker = m.ticker if full else m.ticker[:30]
            title = m.title if full else (m.title[:40] + ("..." if len(m.title) > 40 else ""))
            table.add_row(
                ticker,
                title,
                m.status.value,
                f"{m.yes_bid_cents}¢",
                f"{m.volume_24h:,}",
            )

        from rich.console import Console

        output_console = console if not full else Console(width=200)
        output_console.print(table)
        n, total = min(len(markets), limit), len(markets)
        output_console.print(
            f"\n[dim]Showing {n}{f' of {total}' if total > limit else ''} markets[/dim]"
        )

    asyncio.run(_list())
