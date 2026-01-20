"""Typer CLI commands for portfolio tracking and P&L reporting."""

import os
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.table import Table
from sqlalchemy import select

from kalshi_research.cli.utils import (
    console,
    exit_kalshi_api_error,
    load_json_storage_file,
    run_async,
)
from kalshi_research.paths import DEFAULT_DB_PATH, DEFAULT_THESES_PATH

app = typer.Typer(help="Portfolio tracking and P&L commands.")

PORTFOLIO_SYNC_TIP = (
    "[dim]Tip: run `kalshi portfolio sync` to populate/refresh the local cache.[/dim]"
)


def _format_signed_currency(cents: int) -> str:
    value = f"${cents / 100:.2f}"
    if cents > 0:
        return f"[green]+{value}[/green]"
    if cents < 0:
        return f"[red]{value}[/red]"
    return value


def _load_theses() -> dict[str, Any]:
    """Load theses from storage."""
    return load_json_storage_file(
        path=DEFAULT_THESES_PATH, kind="Theses", required_list_key="theses"
    )


def _validate_environment_override(environment: str | None) -> str | None:
    """Validate and normalize a portfolio `--env` override.

    Args:
        environment: Raw CLI environment value (`demo` or `prod`), or `None`.

    Returns:
        Normalized environment string, or `None` when no override was provided.

    Raises:
        typer.Exit: If the environment value is invalid.
    """
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


def _require_auth_env(
    *, purpose: str, environment: str | None
) -> tuple[str, str | None, str | None]:
    from kalshi_research.api.credentials import (
        get_kalshi_auth_env_var_names,
        resolve_kalshi_auth_env,
    )

    key_id, private_key_path, private_key_b64 = resolve_kalshi_auth_env(environment=environment)
    key_id_var, private_key_path_var, private_key_b64_var = get_kalshi_auth_env_var_names(
        environment=environment
    )

    if not key_id or (not private_key_path and not private_key_b64):
        console.print(f"[red]Error:[/red] {purpose} requires authentication.")
        console.print(
            f"[dim]Set {key_id_var} and {private_key_path_var} "
            f"(or {private_key_b64_var}) to enable authenticated commands.[/dim]"
        )
        raise typer.Exit(1)

    return key_id, private_key_path, private_key_b64


def _resolve_rate_tier_override(rate_tier: str | None) -> str:
    from kalshi_research.api.rate_limiter import RateTier

    raw = rate_tier or os.getenv("KALSHI_RATE_TIER") or RateTier.BASIC.value
    normalized = raw.strip().lower()
    try:
        return RateTier(normalized).value
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid rate tier '{raw}'.")
        console.print("[dim]Expected one of: basic, advanced, premier, prime.[/dim]")
        raise typer.Exit(1) from None


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
    rate_tier: Annotated[
        str | None,
        typer.Option(
            "--rate-tier",
            help=(
                "API rate limit tier (basic/advanced/premier/prime). "
                "Defaults to KALSHI_RATE_TIER or basic."
            ),
            show_default=False,
        ),
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

    Syncs positions, fills, settlements, cost basis (FIFO), mark prices, and unrealized P&L.
    """
    from kalshi_research.api.exceptions import KalshiAPIError
    from kalshi_research.cli.client_factory import authed_client, public_client
    from kalshi_research.cli.db import open_db
    from kalshi_research.portfolio.syncer import PortfolioSyncer

    environment_override = _validate_environment_override(environment)
    key_id, private_key_path, private_key_b64 = _require_auth_env(
        purpose="Portfolio sync", environment=environment_override
    )
    rate_tier_override = _resolve_rate_tier_override(rate_tier)

    async def _sync() -> None:
        try:
            async with (
                authed_client(
                    key_id=key_id,
                    private_key_path=private_key_path,
                    private_key_b64=private_key_b64,
                    environment=environment_override,
                    rate_tier=rate_tier_override,
                ) as client,
                open_db(db_path) as db,
            ):
                syncer = PortfolioSyncer(client=client, db=db)

                # Sync trades first (needed for cost basis calculation)
                console.print("[dim]Syncing trades...[/dim]")
                trades_count = await syncer.sync_trades()
                console.print(f"[green]✓[/green] Synced {trades_count} trades")

                # Sync settlements (needed for complete history and backtesting)
                console.print("[dim]Syncing settlements...[/dim]")
                settlements_count = await syncer.sync_settlements()
                console.print(f"[green]✓[/green] Synced {settlements_count} settlements")

                # Sync positions (computes cost basis from trades via FIFO)
                console.print("[dim]Syncing positions + cost basis (FIFO)...[/dim]")
                positions_count = await syncer.sync_positions()
                console.print(f"[green]✓[/green] Synced {positions_count} positions")

                # Update mark prices + unrealized P&L (requires public API)
                if not skip_mark_prices and positions_count > 0:
                    console.print("[dim]Fetching mark prices...[/dim]")
                    # Use same environment override for public client
                    async with public_client(environment=environment_override) as pub_client:
                        updated = await syncer.update_mark_prices(pub_client)
                        console.print(
                            f"[green]✓[/green] Updated mark prices for {updated} positions"
                        )

                console.print(
                    f"\n[green]✓[/green] Portfolio sync complete: "
                    f"{positions_count} positions, {trades_count} trades, "
                    f"{settlements_count} settlements"
                )

        except KalshiAPIError as e:
            exit_kalshi_api_error(e)
        except (OSError, ValueError) as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

    run_async(_sync())


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


@app.command("pnl")
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

        table.add_row("Realized P&L:", _format_signed_currency(summary.realized_pnl_cents))
        table.add_row(unrealized_label, _format_signed_currency(summary.unrealized_pnl_cents))
        table.add_row("Total P&L:", _format_signed_currency(summary.total_pnl_cents))

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


@app.command("balance")
def portfolio_balance(
    environment: Annotated[
        str | None,
        typer.Option("--env", help="Override global environment (demo or prod)."),
    ] = None,
    rate_tier: Annotated[
        str | None,
        typer.Option(
            "--rate-tier",
            help=(
                "API rate limit tier (basic/advanced/premier/prime). "
                "Defaults to KALSHI_RATE_TIER or basic."
            ),
            show_default=False,
        ),
    ] = None,
) -> None:
    """View account balance."""
    from kalshi_research.api.exceptions import KalshiAPIError
    from kalshi_research.cli.client_factory import authed_client

    environment_override = _validate_environment_override(environment)
    key_id, private_key_path, private_key_b64 = _require_auth_env(
        purpose="Balance", environment=environment_override
    )
    rate_tier_override = _resolve_rate_tier_override(rate_tier)

    async def _balance() -> None:
        from kalshi_research.api.models.portfolio import (  # noqa: TC001
            PortfolioBalance,
        )

        balance: PortfolioBalance | None = None
        try:
            async with authed_client(
                key_id=key_id,
                private_key_path=private_key_path,
                private_key_b64=private_key_b64,
                environment=environment_override,
                rate_tier=rate_tier_override,
            ) as client:
                try:
                    balance = await client.get_balance()
                except KalshiAPIError as e:
                    exit_kalshi_api_error(e)
        except (OSError, ValueError) as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

        if not balance:
            console.print("[yellow]No balance data returned[/yellow]")
            return

        table = Table(title="Account Balance")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        # Convert Pydantic model to dict for display
        balance_dict = balance.model_dump()
        for k, v in sorted(balance_dict.items()):
            table.add_row(str(k), str(v))
        console.print(table)

    run_async(_balance())


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
                position = result.scalar_one_or_none()

                if not position:
                    console.print(f"[yellow]No open position found for {ticker}[/yellow]")
                    console.print(PORTFOLIO_SYNC_TIP)
                    raise typer.Exit(2) from None

                # Update thesis_id
                position.thesis_id = thesis

            console.print(f"[green]✓[/green] Position {ticker} linked to thesis {thesis}")

    run_async(_link())


@app.command("suggest-links")
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
        data = _load_theses()
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
