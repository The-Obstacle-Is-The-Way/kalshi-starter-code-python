"""Market get command - fetch a single market by ticker."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from kalshi_research.cli.utils import console, exit_kalshi_api_error, run_async


def market_get(
    ticker: Annotated[str, typer.Argument(help="Market ticker to fetch.")],
) -> None:
    """Fetch a single market by ticker."""
    from kalshi_research.cli.client_factory import public_client

    async def _get() -> None:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with public_client() as client:
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
