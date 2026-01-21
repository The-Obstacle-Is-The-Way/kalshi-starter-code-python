"""Portfolio history command - view trade history."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - Required at runtime for Typer introspection
from typing import Annotated

import typer
from rich.table import Table
from sqlalchemy import select

from kalshi_research.cli.portfolio._helpers import PORTFOLIO_SYNC_TIP
from kalshi_research.cli.utils import console, run_async
from kalshi_research.paths import DEFAULT_DB_PATH


def portfolio_history(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of trades to show."),
    ] = 20,
    ticker: Annotated[
        str | None,
        typer.Option("--ticker", "-t", help="Filter by specific ticker."),
    ] = None,
) -> None:
    """View trade history."""
    from kalshi_research.cli.db import open_db
    from kalshi_research.portfolio import Trade

    async def _history() -> None:
        async with open_db(db_path) as db, db.session_factory() as session:
            # Build query
            query = select(Trade).order_by(Trade.executed_at.desc()).limit(limit)
            if ticker:
                query = query.where(Trade.ticker == ticker)

            result = await session.execute(query)
            trades = result.scalars().all()

            if not trades:
                console.print("[yellow]No trades found[/yellow]")
                console.print(PORTFOLIO_SYNC_TIP)
                return

            # Display trades table
            table = Table(title=f"Trade History (Last {limit})", show_header=True)
            table.add_column("Date", style="dim")
            table.add_column("Ticker", style="cyan", no_wrap=True)
            table.add_column("Side", style="magenta")
            table.add_column("Action", style="yellow")
            table.add_column("Qty", justify="right")
            table.add_column("Price", justify="right")
            table.add_column("Total", justify="right")

            for trade in trades:
                date_str = trade.executed_at.strftime("%Y-%m-%d %H:%M")
                price_str = f"{trade.price_cents}¢"
                total_str = f"${trade.total_cost_cents / 100:.2f}"

                table.add_row(
                    date_str,
                    trade.ticker,
                    trade.side.upper(),
                    trade.action.upper(),
                    str(trade.quantity),
                    price_str,
                    total_str,
                )

            console.print(table)

    run_async(_history())
