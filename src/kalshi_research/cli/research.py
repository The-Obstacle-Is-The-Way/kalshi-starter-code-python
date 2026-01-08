import asyncio
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from kalshi_research.cli.utils import (
    atomic_write_json,
    console,
    load_json_storage_file,
)
from kalshi_research.paths import DEFAULT_DB_PATH, DEFAULT_THESES_PATH

app = typer.Typer(help="Research and thesis tracking commands.")
thesis_app = typer.Typer(help="Thesis management commands.")
app.add_typer(thesis_app, name="thesis")


def _get_thesis_file() -> Path:
    """Get path to thesis storage file."""
    return DEFAULT_THESES_PATH


def _load_theses() -> dict[str, Any]:
    """Load theses from storage."""
    thesis_file = _get_thesis_file()
    return load_json_storage_file(path=thesis_file, kind="Theses", required_list_key="theses")


def _save_theses(data: dict[str, Any]) -> None:
    """Save theses to storage."""
    thesis_file = _get_thesis_file()
    atomic_write_json(thesis_file, data)


def _parse_backtest_dates(start: str, end: str) -> tuple[datetime, datetime]:
    """Parse and validate backtest dates."""
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError as e:
        console.print(f"[red]Error:[/red] Invalid date format: {e}")
        console.print("[dim]Use YYYY-MM-DD format.[/dim]")
        raise typer.Exit(1) from None

    if start_dt >= end_dt:
        console.print("[red]Error:[/red] Start date must be before end date")
        raise typer.Exit(1)

    return start_dt, end_dt


def _display_backtest_results(results: list[Any], start: str, end: str) -> None:
    """Helper to display backtest results."""
    # Calculate aggregate statistics
    total_trades = sum(r.total_trades for r in results)
    total_pnl = sum(r.total_pnl for r in results)
    total_wins = sum(r.winning_trades for r in results)
    avg_brier = sum(r.brier_score for r in results) / len(results) if results else 0

    # Display summary table
    summary_table = Table(title="Backtest Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Date Range", f"{start} to {end}")
    summary_table.add_row("Theses Tested", str(len(results)))
    summary_table.add_row("Total Trades", str(total_trades))
    summary_table.add_row(
        "Aggregate Win Rate",
        f"{total_wins / total_trades:.1%}" if total_trades > 0 else "N/A",
    )
    pnl_color = "green" if total_pnl >= 0 else "red"
    summary_table.add_row("Total P&L", f"[{pnl_color}]{total_pnl:+.0f}¢[/{pnl_color}]")
    summary_table.add_row("Avg Brier Score", f"{avg_brier:.4f}")

    console.print(summary_table)
    console.print()

    # Display per-thesis results
    detail_table = Table(title="Per-Thesis Results")
    detail_table.add_column("Thesis ID", style="cyan", max_width=15)
    detail_table.add_column("Trades", justify="right")
    detail_table.add_column("Win Rate", justify="right")
    detail_table.add_column("P&L", justify="right")
    detail_table.add_column("Brier", justify="right")
    detail_table.add_column("Sharpe", justify="right")

    for result in sorted(results, key=lambda r: r.total_pnl, reverse=True):
        pnl_str = f"{result.total_pnl:+.0f}¢"
        pnl_color = "green" if result.total_pnl >= 0 else "red"
        detail_table.add_row(
            result.thesis_id[:15],
            str(result.total_trades),
            f"{result.win_rate:.1%}" if result.total_trades > 0 else "N/A",
            f"[{pnl_color}]{pnl_str}[/{pnl_color}]",
            f"{result.brier_score:.4f}",
            f"{result.sharpe_ratio:.2f}" if result.sharpe_ratio != 0 else "N/A",
        )

    console.print(detail_table)


@thesis_app.command("create")
def research_thesis_create(
    title: Annotated[str, typer.Argument(help="Thesis title")],
    markets: Annotated[str, typer.Option("--markets", "-m", help="Comma-separated market tickers")],
    your_prob: Annotated[float, typer.Option("--your-prob", help="Your probability (0-1)")],
    market_prob: Annotated[float, typer.Option("--market-prob", help="Market probability (0-1)")],
    confidence: Annotated[float, typer.Option("--confidence", help="Your confidence (0-1)")],
    bull_case: Annotated[str, typer.Option("--bull", help="Bull case")] = "Why YES",
    bear_case: Annotated[str, typer.Option("--bear", help="Bear case")] = "Why NO",
) -> None:
    """Create a new research thesis."""
    thesis_id = str(uuid.uuid4())
    market_tickers = [t.strip() for t in markets.split(",")]

    thesis = {
        "id": thesis_id,
        "title": title,
        "market_tickers": market_tickers,
        "your_probability": your_prob,
        "market_probability": market_prob,
        "confidence": confidence,
        "bull_case": bull_case,
        "bear_case": bear_case,
        "key_assumptions": [],
        "invalidation_criteria": [],
        "status": "active",
        "created_at": datetime.now(UTC).isoformat(),
        "resolved_at": None,
        "actual_outcome": None,
        "updates": [],
    }

    # Save
    data = _load_theses()
    data.setdefault("theses", []).append(thesis)
    _save_theses(data)

    console.print(f"[green]✓[/green] Thesis created: {title}")
    console.print(f"[dim]ID: {thesis_id[:8]}[/dim]")
    console.print(f"Edge: {(your_prob - market_prob) * 100:.1f}%")


@thesis_app.command("list")
def research_thesis_list() -> None:
    """List all theses."""
    data = _load_theses()
    theses = data.get("theses", [])

    if not theses:
        console.print("[yellow]No theses found.[/yellow]")
        return

    table = Table(title="Research Theses")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="green")
    table.add_column("Edge", style="yellow")

    for thesis in theses:
        edge = (thesis["your_probability"] - thesis["market_probability"]) * 100
        table.add_row(
            thesis["id"][:8],
            thesis["title"][:40],
            thesis["status"],
            f"{edge:+.1f}%",
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(theses)} theses[/dim]")


@thesis_app.command("show")
def research_thesis_show(  # noqa: PLR0915
    thesis_id: Annotated[str, typer.Argument(help="Thesis ID to show")],
    with_positions: Annotated[
        bool, typer.Option("--with-positions", help="Show linked positions")
    ] = False,
    db_path: Annotated[
        Path, typer.Option("--db", "-d", help="Path to SQLite database file.")
    ] = DEFAULT_DB_PATH,
) -> None:
    """Show details of a thesis."""
    data = _load_theses()
    theses = data.get("theses", [])

    # Find thesis
    thesis = None
    for t in theses:
        if t["id"].startswith(thesis_id):
            thesis = t
            break

    if not thesis:
        console.print(f"[yellow]Thesis not found: {thesis_id}[/yellow]")
        return

    # Display
    console.print(f"\n[bold]{thesis['title']}[/bold]")
    console.print(f"[dim]ID: {thesis['id']}[/dim]")
    console.print(f"[dim]Status: {thesis['status']}[/dim]\n")

    table = Table()
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Markets", ", ".join(thesis["market_tickers"]))
    table.add_row("Your Probability", f"{thesis['your_probability']:.1%}")
    table.add_row("Market Probability", f"{thesis['market_probability']:.1%}")
    table.add_row("Confidence", f"{thesis['confidence']:.1%}")
    edge = (thesis["your_probability"] - thesis["market_probability"]) * 100
    table.add_row("Edge", f"{edge:+.1f}%")

    console.print(table)

    console.print(f"\n[cyan]Bull Case:[/cyan] {thesis['bull_case']}")
    console.print(f"[cyan]Bear Case:[/cyan] {thesis['bear_case']}")

    if thesis["updates"]:
        console.print("\n[cyan]Updates:[/cyan]")
        for update in thesis["updates"]:
            console.print(f"  {update['timestamp']}: {update['note']}")

    # Show linked positions if requested
    if with_positions:
        from sqlalchemy import select

        from kalshi_research.data import DatabaseManager
        from kalshi_research.portfolio import Position

        async def _show_positions() -> None:
            db = DatabaseManager(db_path)
            try:
                async with db.session_factory() as session:
                    query = select(Position).where(Position.thesis_id == thesis["id"])
                    result = await session.execute(query)
                    positions = result.scalars().all()

                    if not positions:
                        console.print("\n[dim]No positions linked to this thesis.[/dim]")
                        return

                    # Display positions
                    console.print("\n[cyan]Linked Positions:[/cyan]")
                    pos_table = Table()
                    pos_table.add_column("Ticker", style="cyan")
                    pos_table.add_column("Side", style="magenta")
                    pos_table.add_column("Qty", justify="right")
                    pos_table.add_column("Avg Price", justify="right")
                    pos_table.add_column("P&L", justify="right")

                    for pos in positions:
                        pnl = pos.unrealized_pnl_cents or 0
                        pnl_str = f"${pnl / 100:.2f}"
                        if pnl > 0:
                            pnl_str = f"[green]+{pnl_str}[/green]"
                        elif pnl < 0:
                            pnl_str = f"[red]{pnl_str}[/red]"

                        pos_table.add_row(
                            pos.ticker,
                            pos.side.upper(),
                            str(pos.quantity),
                            f"{pos.avg_price_cents}¢",
                            pnl_str,
                        )

                    console.print(pos_table)
            finally:
                await db.close()

        asyncio.run(_show_positions())


@thesis_app.command("resolve")
def research_thesis_resolve(
    thesis_id: Annotated[str, typer.Argument(help="Thesis ID to resolve")],
    outcome: Annotated[str, typer.Option("--outcome", help="Outcome: yes, no, void")],
) -> None:
    """Resolve a thesis with an outcome."""
    data = _load_theses()
    theses = data.get("theses", [])

    # Find and update thesis
    for thesis in theses:
        if thesis["id"].startswith(thesis_id):
            thesis["status"] = "resolved"
            thesis["resolved_at"] = datetime.now(UTC).isoformat()
            thesis["actual_outcome"] = outcome
            _save_theses(data)
            console.print(f"[green]✓[/green] Thesis resolved: {thesis['title']}")
            console.print(f"Outcome: {outcome}")
            return

    console.print(f"[yellow]Thesis not found: {thesis_id}[/yellow]")


@app.command("backtest")
def research_backtest(
    start: Annotated[str, typer.Option("--start", help="Start date (YYYY-MM-DD)")],
    end: Annotated[str, typer.Option("--end", help="End date (YYYY-MM-DD)")],
    thesis_id: Annotated[
        str | None,
        typer.Option(
            "--thesis",
            "-t",
            help="Specific thesis ID to backtest (default: all resolved)",
        ),
    ] = None,
    db_path: Annotated[
        Path, typer.Option("--db", "-d", help="Path to SQLite database file.")
    ] = DEFAULT_DB_PATH,
) -> None:
    """
    Run backtests on resolved theses using historical settlements.

    Uses the ThesisBacktester class to compute real P&L, win rate, and Brier scores
    from actual settlement data in the database.

    Examples:
        kalshi research backtest --start 2024-01-01 --end 2024-12-31
        kalshi research backtest --thesis abc123 --start 2024-06-01 --end 2024-12-31
    """
    from sqlalchemy import select

    from kalshi_research.data import DatabaseManager
    from kalshi_research.data.models import Settlement
    from kalshi_research.research.backtest import ThesisBacktester
    from kalshi_research.research.thesis import ThesisManager, ThesisStatus

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        console.print("[dim]Run 'kalshi data init' first.[/dim]")
        raise typer.Exit(1)

    async def _backtest() -> None:
        async with DatabaseManager(db_path) as db:
            try:
                thesis_mgr = ThesisManager()
            except ValueError as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

            backtester = ThesisBacktester()

            console.print(f"[dim]Backtesting from {start} to {end}...[/dim]")

            start_dt, end_dt = _parse_backtest_dates(start, end)

            # Load theses
            if thesis_id:
                thesis = thesis_mgr.get(thesis_id)
                if not thesis:
                    console.print(f"[red]Error:[/red] Thesis '{thesis_id}' not found")
                    console.print(
                        "[dim]Use 'kalshi research thesis list' to see available theses.[/dim]"
                    )
                    raise typer.Exit(1)
                theses = [thesis]
            else:
                theses = thesis_mgr.list_all()

            # Filter to resolved theses only
            resolved = [t for t in theses if t.status == ThesisStatus.RESOLVED]
            if not resolved:
                console.print("[yellow]No resolved theses to backtest[/yellow]")
                console.print(
                    "[dim]Theses must be resolved before backtesting. "
                    "Use 'kalshi research thesis resolve'.[/dim]"
                )
                return

            console.print(f"[dim]Found {len(resolved)} resolved theses[/dim]")

            # Load settlements from DB
            async with db.session_factory() as session:
                result = await session.execute(
                    select(Settlement).where(
                        Settlement.settled_at >= start_dt,
                        Settlement.settled_at <= end_dt,
                    )
                )
                settlements = list(result.scalars().all())

            if not settlements:
                console.print(f"[yellow]No settlements found between {start} and {end}[/yellow]")
                console.print(
                    "[dim]Run 'kalshi data sync-settlements' to fetch settlement data.[/dim]"
                )
                return

            console.print(f"[dim]Found {len(settlements)} settlements in date range[/dim]")

            # Run backtest with progress indicator
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(f"Backtesting {len(resolved)} theses...", total=None)
                results = await backtester.backtest_all(resolved, settlements)

            if not results:
                console.print("[yellow]No backtest results generated[/yellow]")
                console.print("[dim]This can happen if no theses match the settlement data.[/dim]")
                return

            _display_backtest_results(results, start, end)

    asyncio.run(_backtest())
