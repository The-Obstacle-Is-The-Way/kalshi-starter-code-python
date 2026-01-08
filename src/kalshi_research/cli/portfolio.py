import asyncio
import os
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.table import Table
from sqlalchemy import select

from kalshi_research.cli.utils import console, load_json_storage_file
from kalshi_research.paths import DEFAULT_DB_PATH, DEFAULT_THESES_PATH

app = typer.Typer(help="Portfolio tracking and P&L commands.")


def _load_theses() -> dict[str, Any]:
    """Load theses from storage."""
    return load_json_storage_file(
        path=DEFAULT_THESES_PATH, kind="Theses", required_list_key="theses"
    )


def _validate_environment_override(environment: str | None) -> str | None:
    if environment is None:
        return None

    from kalshi_research.api.config import Environment

    raw = environment
    normalized = raw.strip().lower()
    try:
        return Environment(normalized).value
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid environment '{raw}'. Expected 'prod' or 'demo'.")
        raise typer.Exit(1) from None


def _require_auth_env(*, purpose: str) -> tuple[str, str | None, str | None]:
    key_id = os.getenv("KALSHI_KEY_ID")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH")
    private_key_b64 = os.getenv("KALSHI_PRIVATE_KEY_B64")

    if not key_id or (not private_key_path and not private_key_b64):
        console.print(f"[red]Error:[/red] {purpose} requires authentication.")
        console.print(
            "[dim]Set KALSHI_KEY_ID and KALSHI_PRIVATE_KEY_PATH "
            "(or KALSHI_PRIVATE_KEY_B64) to enable authenticated commands.[/dim]"
        )
        raise typer.Exit(1)

    return key_id, private_key_path, private_key_b64


@app.command("sync")
def portfolio_sync(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    environment: Annotated[
        str | None,
        typer.Option("--env", help="Override global environment (demo or prod)."),
    ] = None,
    skip_mark_prices: Annotated[
        bool,
        typer.Option(
            "--skip-mark-prices",
            help="Skip fetching current market prices (faster sync).",
        ),
    ] = False,
) -> None:
    """Sync positions and trades from Kalshi API.

    Syncs positions, trades, cost basis (FIFO), mark prices, and unrealized P&L.
    """
    from kalshi_research.api import KalshiClient, KalshiPublicClient
    from kalshi_research.api.exceptions import KalshiAPIError
    from kalshi_research.data import DatabaseManager
    from kalshi_research.portfolio.syncer import PortfolioSyncer

    environment_override = _validate_environment_override(environment)
    key_id, private_key_path, private_key_b64 = _require_auth_env(purpose="Portfolio sync")

    async def _sync() -> None:
        try:
            async with (
                KalshiClient(
                    key_id=key_id,
                    private_key_path=private_key_path,
                    private_key_b64=private_key_b64,
                    environment=environment_override,
                ) as client,
                DatabaseManager(db_path) as db,
            ):
                await db.create_tables()
                syncer = PortfolioSyncer(client=client, db=db)

                # Sync trades first (needed for cost basis calculation)
                console.print("[dim]Syncing trades...[/dim]")
                trades_count = await syncer.sync_trades()
                console.print(f"[green]✓[/green] Synced {trades_count} trades")

                # Sync positions (computes cost basis from trades via FIFO)
                console.print("[dim]Syncing positions + cost basis (FIFO)...[/dim]")
                positions_count = await syncer.sync_positions()
                console.print(f"[green]✓[/green] Synced {positions_count} positions")

                # Update mark prices + unrealized P&L (requires public API)
                if not skip_mark_prices and positions_count > 0:
                    console.print("[dim]Fetching mark prices...[/dim]")
                    # Use same environment override for public client
                    async with KalshiPublicClient(
                        environment=environment_override
                    ) as public_client:
                        updated = await syncer.update_mark_prices(public_client)
                        console.print(
                            f"[green]✓[/green] Updated mark prices for {updated} positions"
                        )

                console.print(
                    f"\n[green]✓[/green] Portfolio sync complete: "
                    f"{positions_count} positions, {trades_count} trades"
                )

        except KalshiAPIError as e:
            console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
            raise typer.Exit(1) from None
        except (OSError, ValueError) as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

    asyncio.run(_sync())


@app.command("positions")
def portfolio_positions(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    ticker: Annotated[
        str | None,
        typer.Option("--ticker", "-t", help="Filter by specific ticker."),
    ] = None,
) -> None:
    """View current positions."""
    from kalshi_research.data import DatabaseManager
    from kalshi_research.portfolio import Position

    async def _positions() -> None:
        db = DatabaseManager(db_path)
        try:
            async with db.session_factory() as session:
                # Build query
                query = select(Position).where(Position.closed_at.is_(None))
                if ticker:
                    query = query.where(Position.ticker == ticker)

                result = await session.execute(query)
                positions = result.scalars().all()

                if not positions:
                    console.print("[yellow]No open positions found[/yellow]")
                    return

                # Display positions table
                table = Table(title="Current Positions", show_header=True)
                table.add_column("Ticker", style="cyan")
                table.add_column("Side", style="magenta")
                table.add_column("Qty", justify="right")
                table.add_column("Avg Price", justify="right")
                table.add_column("Current", justify="right")
                table.add_column("Unrealized P&L", justify="right")

                total_unrealized = 0.0
                for pos in positions:
                    avg_price = f"{pos.avg_price_cents}¢"
                    current = (
                        f"{pos.current_price_cents}¢"
                        if pos.current_price_cents is not None
                        else "-"
                    )

                    unrealized = pos.unrealized_pnl_cents or 0
                    total_unrealized += unrealized

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

                console.print(table)
                console.print(f"\nTotal Unrealized P&L: ${total_unrealized / 100:.2f}")
        finally:
            await db.close()

    asyncio.run(_positions())


@app.command("pnl")
def portfolio_pnl(  # noqa: PLR0915
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    ticker: Annotated[
        str | None,
        typer.Option("--ticker", "-t", help="Filter by specific ticker."),
    ] = None,
) -> None:
    """View profit & loss summary."""
    from kalshi_research.data import DatabaseManager
    from kalshi_research.portfolio import PnLCalculator, Position, Trade

    async def _pnl() -> None:
        db = DatabaseManager(db_path)
        try:
            async with db.session_factory() as session:
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

                # Calculate P&L
                calculator = PnLCalculator()
                summary = calculator.calculate_summary_with_trades(positions, trades)

                # Display summary
                table = Table(title="P&L Summary (All Time)", show_header=False)
                table.add_column("Metric", style="cyan")
                table.add_column("Value", justify="right")

                unrealized_str = f"${summary.unrealized_pnl_cents / 100:.2f}"
                realized_str = f"${summary.realized_pnl_cents / 100:.2f}"
                total_str = f"${summary.total_pnl_cents / 100:.2f}"

                if summary.unrealized_pnl_cents > 0:
                    unrealized_str = f"[green]+{unrealized_str}[/green]"
                elif summary.unrealized_pnl_cents < 0:
                    unrealized_str = f"[red]{unrealized_str}[/red]"

                if summary.realized_pnl_cents > 0:
                    realized_str = f"[green]+{realized_str}[/green]"
                elif summary.realized_pnl_cents < 0:
                    realized_str = f"[red]{realized_str}[/red]"

                if summary.total_pnl_cents > 0:
                    total_str = f"[green]+{total_str}[/green]"
                elif summary.total_pnl_cents < 0:
                    total_str = f"[red]{total_str}[/red]"

                table.add_row("Realized P&L:", realized_str)
                table.add_row("Unrealized P&L:", unrealized_str)
                table.add_row("Total P&L:", total_str)
                table.add_row("", "")
                table.add_row("Total Trades:", str(summary.total_trades))
                table.add_row("Win Rate:", f"{summary.win_rate * 100:.1f}%")
                table.add_row("Avg Win:", f"${summary.avg_win_cents / 100:.2f}")
                table.add_row("Avg Loss:", f"${summary.avg_loss_cents / 100:.2f}")
                table.add_row("Profit Factor:", f"{summary.profit_factor:.2f}")

                console.print(table)
        finally:
            await db.close()

    asyncio.run(_pnl())


@app.command("balance")
def portfolio_balance(
    environment: Annotated[
        str | None,
        typer.Option("--env", help="Override global environment (demo or prod)."),
    ] = None,
) -> None:
    """View account balance."""
    from kalshi_research.api import KalshiClient
    from kalshi_research.api.exceptions import KalshiAPIError

    environment_override = _validate_environment_override(environment)
    key_id, private_key_path, private_key_b64 = _require_auth_env(purpose="Balance")

    async def _balance() -> None:
        balance: dict[str, Any] | None = None
        try:
            async with KalshiClient(
                key_id=key_id,
                private_key_path=private_key_path,
                private_key_b64=private_key_b64,
                environment=environment_override,
            ) as client:
                try:
                    balance = await client.get_balance()
                except KalshiAPIError as e:
                    console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
                    raise typer.Exit(1) from None
        except (OSError, ValueError) as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

        if not balance:
            console.print("[yellow]No balance data returned[/yellow]")
            return

        table = Table(title="Account Balance")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        for k, v in sorted(balance.items()):
            table.add_row(str(k), str(v))
        console.print(table)

    asyncio.run(_balance())


@app.command("history")
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
    from kalshi_research.data import DatabaseManager
    from kalshi_research.portfolio import Trade

    async def _history() -> None:
        db = DatabaseManager(db_path)
        try:
            async with db.session_factory() as session:
                # Build query
                query = select(Trade).order_by(Trade.executed_at.desc()).limit(limit)
                if ticker:
                    query = query.where(Trade.ticker == ticker)

                result = await session.execute(query)
                trades = result.scalars().all()

                if not trades:
                    console.print("[yellow]No trades found[/yellow]")
                    return

                # Display trades table
                table = Table(title=f"Trade History (Last {limit})", show_header=True)
                table.add_column("Date", style="dim")
                table.add_column("Ticker", style="cyan")
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
        finally:
            await db.close()

    asyncio.run(_history())


@app.command("link")
def portfolio_link(
    ticker: Annotated[str, typer.Argument(help="Market ticker to link")],
    thesis: Annotated[str, typer.Option("--thesis", help="Thesis ID to link to")],
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
) -> None:
    """Link a position to a thesis."""
    from kalshi_research.data import DatabaseManager
    from kalshi_research.portfolio import Position

    async def _link() -> None:
        db = DatabaseManager(db_path)
        try:
            async with db.session_factory() as session:
                # Find open position
                query = select(Position).where(
                    Position.ticker == ticker, Position.closed_at.is_(None)
                )
                result = await session.execute(query)
                position = result.scalar_one_or_none()

                if not position:
                    console.print(f"[yellow]No open position found for {ticker}[/yellow]")
                    return

                # Update thesis_id
                position.thesis_id = thesis
                await session.commit()

                console.print(f"[green]✓[/green] Position {ticker} linked to thesis {thesis}")
        finally:
            await db.close()

    asyncio.run(_link())


@app.command("suggest-links")
def portfolio_suggest_links(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
) -> None:
    """Suggest thesis-position links based on matching tickers."""
    from kalshi_research.data import DatabaseManager
    from kalshi_research.portfolio import Position

    async def _suggest() -> None:
        # Load theses
        data = _load_theses()
        theses = data.get("theses", [])

        if not theses:
            console.print("[yellow]No theses found.[/yellow]")
            return

        # Get unlinked positions
        db = DatabaseManager(db_path)
        try:
            async with db.session_factory() as session:
                query = select(Position).where(
                    Position.thesis_id.is_(None), Position.closed_at.is_(None)
                )
                result = await session.execute(query)
                positions = result.scalars().all()

                if not positions:
                    console.print("[yellow]No unlinked positions found.[/yellow]")
                    return

                # Find matches
                matches = []
                for pos in positions:
                    for thesis in theses:
                        if pos.ticker in thesis.get("market_tickers", []):
                            matches.append(
                                {
                                    "ticker": pos.ticker,
                                    "thesis_id": thesis["id"],
                                    "thesis_title": thesis["title"],
                                }
                            )

                if not matches:
                    console.print("[yellow]No matching thesis-position pairs found.[/yellow]")
                    return

                # Display suggestions
                table = Table(title="Suggested Thesis-Position Links")
                table.add_column("Ticker", style="cyan")
                table.add_column("Thesis ID", style="magenta")
                table.add_column("Thesis Title", style="white")

                for match in matches:
                    table.add_row(
                        match["ticker"],
                        match["thesis_id"][:8],
                        match["thesis_title"],
                    )

                console.print(table)
                console.print(
                    "\n[dim]To link: kalshi portfolio link TICKER --thesis THESIS_ID[/dim]"
                )
        finally:
            await db.close()

    asyncio.run(_suggest())
