"""Portfolio P&L command - view profit and loss summary."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - Required at runtime for Typer introspection
from typing import Annotated

import typer
from rich.table import Table
from sqlalchemy import select

from kalshi_research.cli.portfolio._helpers import format_signed_currency
from kalshi_research.cli.utils import console, run_async
from kalshi_research.paths import DEFAULT_DB_PATH


def portfolio_pnl(
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
    """View profit & loss summary."""
    from kalshi_research.cli.db import open_db
    from kalshi_research.portfolio import PnLCalculator, PnLSummary, Position, Trade
    from kalshi_research.portfolio.models import PortfolioSettlement

    output_console = console if not full else console.__class__(width=200)

    def _build_summary_table(summary: PnLSummary) -> Table:
        table = Table(title="P&L Summary (Synced History)", show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")

        unrealized_label = "Unrealized P&L:"
        if summary.unrealized_positions_unknown:
            unrealized_label = "Unrealized P&L (known only):"

        table.add_row("Realized P&L:", format_signed_currency(summary.realized_pnl_cents))
        table.add_row(unrealized_label, format_signed_currency(summary.unrealized_pnl_cents))
        table.add_row("Total P&L:", format_signed_currency(summary.total_pnl_cents))

        if summary.unrealized_positions_unknown:
            table.add_row("Unknown unrealized rows:", str(summary.unrealized_positions_unknown))
        if summary.orphan_sell_qty_skipped:
            table.add_row("Orphan sell qty skipped:", str(summary.orphan_sell_qty_skipped))
            table.add_row(
                "Note:",
                "[yellow]Trade history incomplete; trade stats are partial.[/yellow]",
            )

        table.add_row("", "")
        table.add_row("Total Trades:", str(summary.total_trades))
        table.add_row("Win Rate:", f"{summary.win_rate * 100:.1f}%")
        table.add_row("Avg Win:", f"${summary.avg_win_cents / 100:.2f}")
        table.add_row("Avg Loss:", f"${summary.avg_loss_cents / 100:.2f}")
        table.add_row("Profit Factor:", f"{summary.profit_factor:.2f}")
        return table

    async def _pnl() -> None:
        async with open_db(db_path) as db, db.session_factory() as session:
            # Get positions
            pos_query = select(Position)
            if ticker:
                pos_query = pos_query.where(Position.ticker == ticker)

            pos_result = await session.execute(pos_query)
            positions = list(pos_result.scalars().all())

            # Get trades
            trade_query = select(Trade)
            if ticker:
                trade_query = trade_query.where(Trade.ticker == ticker)

            trade_result = await session.execute(trade_query)
            trades = list(trade_result.scalars().all())

            # Get settlements (for complete history and resolved-market P&L)
            settlement_query = select(PortfolioSettlement)
            if ticker:
                settlement_query = settlement_query.where(PortfolioSettlement.ticker == ticker)

            settlement_result = await session.execute(settlement_query)
            settlements = list(settlement_result.scalars().all())

            # Calculate P&L
            calculator = PnLCalculator()
            summary = calculator.calculate_summary_with_trades(
                positions=positions,
                trades=trades,
                settlements=settlements,
            )

            # Display summary
            output_console.print(_build_summary_table(summary))

    run_async(_pnl())
