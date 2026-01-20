"""Typer CLI command for thesis backtesting."""

from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from kalshi_research.cli.utils import console, run_async
from kalshi_research.paths import DEFAULT_DB_PATH


def _parse_backtest_dates(start: str, end: str) -> tuple[datetime, datetime]:
    """Parse and validate backtest dates.

    Returns:
        Tuple of (start_datetime, end_datetime_exclusive) where end is midnight
        of the day AFTER the end date to include the full end day.
    """
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except ValueError as e:
        console.print(f"[red]Error:[/red] Invalid date format: {e}")
        console.print("[dim]Use YYYY-MM-DD format.[/dim]")
        raise typer.Exit(1) from None

    if start_date > end_date:
        console.print("[red]Error:[/red] Start date must be on or before end date")
        raise typer.Exit(1)

    start_dt = datetime.combine(start_date, time.min, tzinfo=UTC)
    end_dt_exclusive = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC)

    return start_dt, end_dt_exclusive


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


def research_backtest(
    start: Annotated[str, typer.Option("--start", help="Start date (YYYY-MM-DD)")],
    end: Annotated[str, typer.Option("--end", help="End date (YYYY-MM-DD, inclusive)")],
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

    from kalshi_research.cli.db import open_db
    from kalshi_research.data.models import Settlement
    from kalshi_research.research.backtest import ThesisBacktester
    from kalshi_research.research.thesis import ThesisManager, ThesisStatus

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        console.print("[dim]Run 'kalshi data init' first.[/dim]")
        raise typer.Exit(1)

    async def _backtest() -> None:
        async with open_db(db_path) as db:
            try:
                thesis_mgr = ThesisManager()
            except ValueError as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

            backtester = ThesisBacktester()

            console.print(f"[dim]Backtesting from {start} to {end}...[/dim]")

            start_dt, end_dt_exclusive = _parse_backtest_dates(start, end)

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
                        Settlement.settled_at < end_dt_exclusive,
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

    run_async(_backtest())
