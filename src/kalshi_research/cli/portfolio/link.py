"""Portfolio link commands - link positions to theses."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - Required at runtime for Typer introspection
from typing import Annotated

import typer
from rich.table import Table
from sqlalchemy import select

from kalshi_research.cli.portfolio._helpers import PORTFOLIO_SYNC_TIP, load_theses
from kalshi_research.cli.utils import console, run_async
from kalshi_research.paths import DEFAULT_DB_PATH


def portfolio_link(
    ticker: Annotated[str, typer.Argument(help="Market ticker to link")],
    thesis: Annotated[str, typer.Option("--thesis", help="Thesis ID to link to")],
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
) -> None:
    """Link a position to a thesis."""
    from kalshi_research.cli.db import open_db
    from kalshi_research.portfolio import Position

    async def _link() -> None:
        async with open_db(db_path) as db, db.session_factory() as session:
            async with session.begin():
                # Find open position
                query = select(Position).where(
                    Position.ticker == ticker,
                    Position.closed_at.is_(None),
                    Position.quantity > 0,
                )
                result = await session.execute(query)
                positions = list(result.scalars().all())

                if not positions:
                    console.print(f"[yellow]No open position found for {ticker}[/yellow]")
                    console.print(PORTFOLIO_SYNC_TIP)
                    raise typer.Exit(2) from None

                # Update thesis_id (all open positions for ticker).
                for position in positions:
                    position.thesis_id = thesis

            if len(positions) > 1:
                console.print(
                    f"[yellow]Warning:[/yellow] Multiple open positions found for {ticker}; "
                    f"updated {len(positions)} rows."
                )
            console.print(f"[green]✓[/green] Position(s) {ticker} linked to thesis {thesis}")

    run_async(_link())


def portfolio_suggest_links(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
) -> None:
    """Suggest thesis-position links based on matching tickers."""
    from kalshi_research.cli.db import open_db
    from kalshi_research.portfolio import Position

    async def _suggest() -> None:
        # Load theses
        data = load_theses()
        theses = data.get("theses", [])

        if not theses:
            console.print("[yellow]No theses found.[/yellow]")
            return

        # Get unlinked positions
        async with open_db(db_path) as db, db.session_factory() as session:
            query = select(Position).where(
                Position.thesis_id.is_(None),
                Position.closed_at.is_(None),
                Position.quantity > 0,
            )
            result = await session.execute(query)
            positions = result.scalars().all()

            if not positions:
                console.print("[yellow]No unlinked positions found.[/yellow]")
                console.print(PORTFOLIO_SYNC_TIP)
                return

            # Find matches
            matches = []
            for pos in positions:
                for thesis_item in theses:
                    if pos.ticker in thesis_item.get("market_tickers", []):
                        matches.append(
                            {
                                "ticker": pos.ticker,
                                "thesis_id": thesis_item["id"],
                                "thesis_title": thesis_item["title"],
                            }
                        )

            if not matches:
                console.print("[yellow]No matching thesis-position pairs found.[/yellow]")
                return

            # Display suggestions
            table = Table(title="Suggested Thesis-Position Links")
            table.add_column("Ticker", style="cyan", no_wrap=True)
            table.add_column("Thesis ID", style="magenta")
            table.add_column("Thesis Title", style="white")

            for match in matches:
                table.add_row(
                    match["ticker"],
                    match["thesis_id"][:8],
                    match["thesis_title"],
                )

            console.print(table)
            console.print("\n[dim]To link: kalshi portfolio link TICKER --thesis THESIS_ID[/dim]")

    run_async(_suggest())
