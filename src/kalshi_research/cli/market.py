import asyncio
from typing import Annotated

import typer
from rich.table import Table

from kalshi_research.cli.utils import console

app = typer.Typer(help="Market lookup commands.")


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
        table.add_row("Yes Bid/Ask", f"{market.yes_bid}¢ / {market.yes_ask}¢")
        table.add_row("No Bid/Ask", f"{market.no_bid}¢ / {market.no_ask}¢")
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

        yes_bids = orderbook.yes or []
        no_bids = orderbook.no or []
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


@app.command("list")
def market_list(
    status: Annotated[
        str | None,
        typer.Option("--status", "-s", help="Filter by status (open, closed, etc)."),
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
        async with KalshiPublicClient() as client:
            markets = await client.get_markets(
                status=status,
                event_ticker=event,
                limit=limit,
            )

        if not markets:
            console.print("[yellow]No markets found.[/yellow]")
            return

        table = Table(title=f"Markets (status={status})")
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
                f"{m.yes_bid}¢",
                f"{m.volume_24h:,}",
            )

        console.print(table)
        console.print(f"\n[dim]Showing {len(markets)} markets[/dim]")

    asyncio.run(_list())
