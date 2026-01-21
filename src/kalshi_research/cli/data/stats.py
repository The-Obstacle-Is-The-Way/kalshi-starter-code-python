"""Database statistics command."""

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from kalshi_research.cli.utils import console, run_async
from kalshi_research.paths import DEFAULT_DB_PATH


def data_stats(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
) -> None:
    """Show database statistics."""
    from kalshi_research.cli.db import open_db_session
    from kalshi_research.data.repositories import (
        EventRepository,
        MarketRepository,
        PriceRepository,
    )

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        raise typer.Exit(1)

    async def _stats() -> None:
        async with open_db_session(db_path) as session:
            event_repo = EventRepository(session)
            market_repo = MarketRepository(session)
            price_repo = PriceRepository(session)

            events = await event_repo.get_all()
            markets = await market_repo.get_all()
            market_counts = await market_repo.count_by_status()

            # Sample snapshot counts for a few markets
            active_markets = await market_repo.get_active()
            sample_markets = list(active_markets)[:5]
            snapshot_counts = {}
            for m in sample_markets:
                snapshot_counts[m.ticker] = await price_repo.count_for_market(m.ticker)

        table = Table(title="Database Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Events", str(len(events)))
        table.add_row("Total Markets", str(len(markets)))

        for status, count in sorted(market_counts.items()):
            table.add_row(f"  - {status}", str(count))

        if snapshot_counts:
            table.add_row("Sample Snapshot Counts", "")
            for ticker, count in snapshot_counts.items():
                table.add_row(f"  - {ticker}", str(count))

        console.print(table)

    run_async(_stats())
