"""Portfolio positions command - view current positions."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - Required at runtime for Typer introspection
from typing import Annotated

import typer
from rich.table import Table
from sqlalchemy import select

from kalshi_research.cli.portfolio._helpers import PORTFOLIO_SYNC_TIP
from kalshi_research.cli.utils import console, run_async
from kalshi_research.paths import DEFAULT_DB_PATH


def portfolio_positions(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    ticker: Annotated[
        str | None,
        typer.Option("--ticker", "-t", help="Filter by specific ticker."),
    ] = None,
    full: Annotated[
        bool,
        typer.Option("--full", "-F", help="Show full tickers without truncation."),
    ] = False,
) -> None:
    """View current positions."""
    from kalshi_research.cli.db import open_db
    from kalshi_research.portfolio import Position

    output_console = console if not full else console.__class__(width=200)

    async def _positions() -> None:
        async with open_db(db_path) as db, db.session_factory() as session:
            # Build query
            query = select(Position).where(Position.closed_at.is_(None), Position.quantity > 0)
            if ticker:
                query = query.where(Position.ticker == ticker)

            result = await session.execute(query)
            positions = result.scalars().all()

            if not positions:
                output_console.print("[yellow]No open positions found[/yellow]")
                output_console.print(PORTFOLIO_SYNC_TIP)
                return

            # Display positions table
            table = Table(title="Current Positions", show_header=True)
            table.add_column("Ticker", style="cyan", no_wrap=True)
            table.add_column("Side", style="magenta")
            table.add_column("Qty", justify="right")
            table.add_column("Avg Price", justify="right")
            table.add_column("Current", justify="right")
            table.add_column("Unrealized P&L", justify="right")

            total_unrealized_cents = 0
            unknown_unrealized = 0
            for pos in positions:
                avg_price = "-" if pos.avg_price_cents == 0 else f"{pos.avg_price_cents}¢"
                current = (
                    f"{pos.current_price_cents}¢" if pos.current_price_cents is not None else "-"
                )

                pnl_str = "-"
                if pos.unrealized_pnl_cents is None:
                    unknown_unrealized += 1
                else:
                    unrealized = pos.unrealized_pnl_cents
                    total_unrealized_cents += unrealized

                    pnl_str = f"${unrealized / 100:.2f}"
                    if unrealized > 0:
                        pnl_str = f"[green]+{pnl_str}[/green]"
                    elif unrealized < 0:
                        pnl_str = f"[red]{pnl_str}[/red]"

                table.add_row(
                    pos.ticker,
                    pos.side.upper(),
                    str(pos.quantity),
                    avg_price,
                    current,
                    pnl_str,
                )

            output_console.print(table)
            total_label = "Total Unrealized P&L"
            if unknown_unrealized:
                total_label = "Total Unrealized P&L (known only)"
            output_console.print(f"\n{total_label}: ${total_unrealized_cents / 100:.2f}")
            if unknown_unrealized:
                output_console.print(
                    f"[yellow]{unknown_unrealized} position(s) have unknown unrealized P&L "
                    "(missing cost basis or mark prices).[/yellow]"
                )

    run_async(_positions())
