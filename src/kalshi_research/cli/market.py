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
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum number of results."),
    ] = 20,
) -> None:
    """List markets with optional filters."""
    from kalshi_research.api import KalshiPublicClient

    async def _list() -> None:
        from kalshi_research.api.exceptions import KalshiAPIError

        status_filter = _normalize_market_list_status(status)

        try:
            async with KalshiPublicClient() as client:
                markets = await client.get_markets(
                    status=status_filter,
                    event_ticker=event,
                    limit=limit,
                )
        except KalshiAPIError as e:
            console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
            raise typer.Exit(1) from None
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

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
            table.add_row(
                m.ticker[:30],
                m.title[:40] + ("..." if len(m.title) > 40 else ""),
                m.status.value,
                f"{m.yes_bid_cents}¢",
                f"{m.volume_24h:,}",
            )

        console.print(table)
        console.print(f"\n[dim]Showing {len(markets)} markets[/dim]")

    asyncio.run(_list())
