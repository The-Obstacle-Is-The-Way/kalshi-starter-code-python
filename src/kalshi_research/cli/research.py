import asyncio
import json
import uuid
from dataclasses import asdict
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from kalshi_research.cli.utils import (
    atomic_write_json,
    console,
    load_json_storage_file,
)
from kalshi_research.paths import DEFAULT_DB_PATH, DEFAULT_THESES_PATH

if TYPE_CHECKING:
    from kalshi_research.api.models.market import Market
    from kalshi_research.research.context import MarketResearch, ResearchSource
    from kalshi_research.research.thesis import ThesisEvidence
    from kalshi_research.research.thesis_research import ResearchedThesisData
    from kalshi_research.research.topic import TopicResearch

app = typer.Typer(help="Research and thesis tracking commands.")
thesis_app = typer.Typer(help="Thesis management commands.")
app.add_typer(thesis_app, name="thesis")
cache_app = typer.Typer(help="Exa cache maintenance commands.")
app.add_typer(cache_app, name="cache")


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


@cache_app.command("clear")
def research_cache_clear(
    clear_all: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Clear all cache entries (default: clear expired only).",
        ),
    ] = False,
    cache_dir: Annotated[
        Path | None,
        typer.Option(
            "--cache-dir",
            help="Optional override for Exa cache directory (default: data/exa_cache/).",
        ),
    ] = None,
) -> None:
    """Clear Exa response cache entries on disk."""
    from kalshi_research.exa.cache import ExaCache

    cache = ExaCache(cache_dir) if cache_dir else ExaCache()
    removed = cache.clear() if clear_all else cache.clear_expired()

    mode = "all" if clear_all else "expired"
    console.print(f"[green]✓[/green] Cleared {removed} Exa cache entries ({mode})")


def _parse_backtest_dates(start: str, end: str) -> tuple[datetime, datetime]:
    """Parse and validate backtest dates."""
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


def _serialize_thesis_evidence(evidence_items: "list[ThesisEvidence]") -> list[dict[str, Any]]:
    return [
        {
            "url": e.url,
            "title": e.title,
            "source_domain": e.source_domain,
            "published_date": e.published_date.isoformat() if e.published_date else None,
            "snippet": e.snippet,
            "supports": e.supports,
            "relevance_score": e.relevance_score,
            "added_at": e.added_at.isoformat(),
        }
        for e in evidence_items
    ]


async def _gather_thesis_research_data(
    market_ticker: str,
    *,
    thesis_direction: str,
) -> "ResearchedThesisData":
    from kalshi_research.exa import ExaClient
    from kalshi_research.research.thesis_research import ThesisResearcher

    market = await _fetch_market(market_ticker)
    async with ExaClient.from_env() as exa:
        researcher = ThesisResearcher(exa)
        return await researcher.research_for_thesis(market, thesis_direction=thesis_direction)


@thesis_app.command("create")
def research_thesis_create(
    title: Annotated[str, typer.Argument(help="Thesis title")],
    markets: Annotated[str, typer.Option("--markets", "-m", help="Comma-separated market tickers")],
    your_prob: Annotated[float, typer.Option("--your-prob", help="Your probability (0-1)")],
    market_prob: Annotated[float, typer.Option("--market-prob", help="Market probability (0-1)")],
    confidence: Annotated[float, typer.Option("--confidence", help="Your confidence (0-1)")],
    bull_case: Annotated[str, typer.Option("--bull", help="Bull case")] = "Why YES",
    bear_case: Annotated[str, typer.Option("--bear", help="Bear case")] = "Why NO",
    with_research: Annotated[
        bool, typer.Option("--with-research", help="Attach Exa research evidence to this thesis")
    ] = False,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help=(
                "Accept research suggestions without prompting "
                "(only relevant with --with-research)."
            ),
        ),
    ] = False,
) -> None:
    """Create a new research thesis."""
    thesis_id = str(uuid.uuid4())
    market_tickers = [t.strip() for t in markets.split(",")]

    final_bull = bull_case
    final_bear = bear_case
    evidence: list[dict[str, Any]] = []
    research_summary: str | None = None
    last_research_at: str | None = None

    if with_research and market_tickers:
        console.print("[dim]🔍 Researching thesis...[/dim]")

        try:
            direction = "yes" if your_prob > 0.5 else "no"
            research_data = asyncio.run(
                _gather_thesis_research_data(market_tickers[0], thesis_direction=direction)
            )
        except ValueError as e:
            console.print(f"[yellow]Research skipped:[/yellow] {e}")
        else:
            total_sources = (
                len(research_data.bull_evidence)
                + len(research_data.bear_evidence)
                + len(research_data.neutral_evidence)
            )
            console.print(f"[green]📰 Found {total_sources} relevant sources[/green]\n")

            console.print("[bold cyan]Suggested Bull Case:[/bold cyan]")
            console.print(research_data.suggested_bull_case)
            console.print()

            console.print("[bold cyan]Suggested Bear Case:[/bold cyan]")
            console.print(research_data.suggested_bear_case)
            console.print()

            accept = yes or typer.confirm("Accept these suggestions?", default=True)
            if accept:
                final_bull = research_data.suggested_bull_case
                final_bear = research_data.suggested_bear_case

            evidence = _serialize_thesis_evidence(
                research_data.bull_evidence
                + research_data.bear_evidence
                + research_data.neutral_evidence
            )
            research_summary = research_data.summary
            last_research_at = datetime.now(UTC).isoformat() if evidence else None
            console.print(f"[dim]Research cost: ${research_data.exa_cost_dollars:.4f}[/dim]")

    thesis = {
        "id": thesis_id,
        "title": title,
        "market_tickers": market_tickers,
        "your_probability": your_prob,
        "market_probability": market_prob,
        "confidence": confidence,
        "bull_case": final_bull,
        "bear_case": final_bear,
        "key_assumptions": [],
        "invalidation_criteria": [],
        "status": "active",
        "created_at": datetime.now(UTC).isoformat(),
        "resolved_at": None,
        "actual_outcome": None,
        "updates": [],
        "evidence": evidence,
        "research_summary": research_summary,
        "last_research_at": last_research_at,
    }

    # Save
    data = _load_theses()
    data.setdefault("theses", []).append(thesis)
    _save_theses(data)

    console.print(f"[green]✓[/green] Thesis created: {title}")
    console.print(f"[dim]ID: {thesis_id[:8]}[/dim]")
    console.print(f"Edge: {(your_prob - market_prob) * 100:.1f}%")
    if evidence:
        console.print(f"[dim]Evidence attached: {len(evidence)} sources[/dim]")


@thesis_app.command("list")
def research_thesis_list(
    full: Annotated[
        bool,
        typer.Option("--full", "-F", help="Show full thesis IDs/titles without truncation."),
    ] = False,
) -> None:
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
            thesis["id"] if full else thesis["id"][:8],
            thesis["title"] if full else thesis["title"][:40],
            thesis["status"],
            f"{edge:+.1f}%",
        )

    from rich.console import Console

    output_console = console if not full else Console(width=200)
    output_console.print(table)
    output_console.print(f"\n[dim]Total: {len(theses)} theses[/dim]")


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

    if thesis.get("research_summary"):
        console.print("\n[cyan]Research Summary:[/cyan]")
        console.print(thesis["research_summary"])

    evidence = thesis.get("evidence") or []
    if isinstance(evidence, list) and evidence:
        console.print("\n[cyan]Evidence:[/cyan]")

        def _print_evidence_group(label: str, title: str) -> None:
            items = [e for e in evidence if isinstance(e, dict) and e.get("supports") == label]
            if not items:
                return
            console.print(f"[bold]{title}[/bold]")
            for item in items[:3]:
                item_title = str(item.get("title", "")).strip()
                domain = str(item.get("source_domain", "")).strip()
                console.print(f"  • {item_title} [dim]({domain})[/dim]")
                snippet = str(item.get("snippet", "")).strip()
                if snippet:
                    snippet_preview = snippet[:180] + ("..." if len(snippet) > 180 else "")
                    console.print(f"    [dim]{snippet_preview}[/dim]")

        _print_evidence_group("bull", "🟢 Bull Evidence")
        _print_evidence_group("bear", "🔴 Bear Evidence")
        _print_evidence_group("neutral", "⚪ Neutral Evidence")

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
                        pnl_str = "-"
                        if pos.unrealized_pnl_cents is not None:
                            pnl = pos.unrealized_pnl_cents
                            pnl_str = f"${pnl / 100:.2f}"
                            if pnl > 0:
                                pnl_str = f"[green]+{pnl_str}[/green]"
                            elif pnl < 0:
                                pnl_str = f"[red]{pnl_str}[/red]"

                        pos_table.add_row(
                            pos.ticker,
                            pos.side.upper(),
                            str(pos.quantity),
                            "-" if pos.avg_price_cents == 0 else f"{pos.avg_price_cents}¢",
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


@thesis_app.command("check-invalidation")
def research_thesis_check_invalidation(
    thesis_id: Annotated[str, typer.Argument(help="Thesis ID to check")],
    hours: Annotated[int, typer.Option("--hours", "-h", help="Lookback hours")] = 48,
) -> None:
    """Check for signals that might invalidate your thesis."""
    from kalshi_research.exa import ExaClient
    from kalshi_research.research.invalidation import InvalidationDetector, InvalidationSeverity
    from kalshi_research.research.thesis import ThesisTracker

    async def _check() -> None:
        try:
            tracker = ThesisTracker(_get_thesis_file())
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

        thesis = tracker.get(thesis_id)
        if not thesis:
            for t in tracker.list_all():
                if t.id.startswith(thesis_id):
                    thesis = t
                    break

        if not thesis:
            console.print(f"[yellow]Thesis not found: {thesis_id}[/yellow]")
            return

        console.print(f"\n[bold]Thesis:[/bold] {thesis.title}")
        console.print(f"Your probability: {thesis.your_probability:.0%} YES")
        console.print(f"[dim]Checking last {hours} hours...[/dim]\n")

        try:
            async with ExaClient.from_env() as exa:
                detector = InvalidationDetector(exa, lookback_hours=hours)
                report = await detector.check_thesis(thesis)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print("[dim]Set EXA_API_KEY in your environment or .env file.[/dim]")
            raise typer.Exit(1) from None

        if not report.signals:
            console.print("[green]✓ No invalidation signals found[/green]")
            console.print(f"[dim]{report.recommendation}[/dim]")
            return

        console.print("[yellow]⚠️ Potential Invalidation Signals[/yellow]")
        console.print("─" * 50)

        for signal in report.signals:
            severity = signal.severity
            label = severity.value.upper()
            color = (
                "red"
                if severity == InvalidationSeverity.HIGH
                else "yellow"
                if severity == InvalidationSeverity.MEDIUM
                else "white"
            )
            console.print(f"[{color}][{label}][/{color}] {signal.title}")
            console.print(f"  [dim]{signal.source_domain} | {signal.url}[/dim]")
            if signal.reason:
                console.print(f"  [dim]{signal.reason}[/dim]")
            if signal.snippet:
                console.print(f"  [italic]> {signal.snippet[:200]}[/italic]")
            console.print()

        if report.recommendation:
            console.print(f"[bold]Recommendation:[/bold] {report.recommendation}")

    asyncio.run(_check())


@thesis_app.command("suggest")
def research_thesis_suggest(
    category: Annotated[
        str | None,
        typer.Option("--category", "-c", help="Optional category filter (crypto, politics, etc.)"),
    ] = None,
) -> None:
    """Generate thesis ideas from Exa research."""
    from kalshi_research.exa import ExaClient
    from kalshi_research.research.thesis_research import ThesisSuggester

    async def _suggest() -> None:
        try:
            async with ExaClient.from_env() as exa:
                suggester = ThesisSuggester(exa)
                suggestions = await suggester.suggest_theses(category=category)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print("[dim]Set EXA_API_KEY in your environment or .env file.[/dim]")
            raise typer.Exit(1) from None

        if not suggestions:
            console.print("[yellow]No suggestions found.[/yellow]")
            return

        console.print("\n[bold]🎯 Thesis Suggestions Based on Research[/bold]")
        console.print("─" * 60)
        for i, s in enumerate(suggestions, 1):
            console.print(f"\n[bold]{i}. {s.suggested_thesis}[/bold]")
            console.print(f"[dim]Source:[/dim] {s.source_title} ({s.source_url})")
            if s.key_insight:
                console.print(f"[italic]> {s.key_insight[:200]}[/italic]")

    asyncio.run(_suggest())


@app.command("backtest")
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

    asyncio.run(_backtest())


def _print_market_news(sources: list["ResearchSource"]) -> None:
    console.print("[bold cyan]📰 Recent News[/bold cyan]")
    console.print("─" * 40)
    for i, source in enumerate(sources[:5], 1):
        date_str = source.published_date.strftime("%b %d") if source.published_date else "N/A"
        console.print(f"{i}. [bold]{source.title}[/bold] ({date_str})")
        console.print(f"   [dim]Source: {source.source_domain}[/dim]")
        if source.highlight:
            snippet = source.highlight[:150]
            if len(source.highlight) > 150:
                snippet += "..."
            console.print(f"   [italic]> {snippet}[/italic]")
        console.print()


def _print_market_papers(sources: list["ResearchSource"]) -> None:
    console.print("[bold cyan]📄 Research Papers[/bold cyan]")
    console.print("─" * 40)
    for i, source in enumerate(sources[:3], 1):
        console.print(f"{i}. [bold]{source.title}[/bold]")
        console.print(f"   [dim]Source: {source.source_domain}[/dim]")
        console.print()


def _print_market_related(sources: list["ResearchSource"]) -> None:
    console.print("[bold cyan]🔗 Related Coverage[/bold cyan]")
    console.print("─" * 40)
    for source in sources[:3]:
        console.print(f"  • {source.title}")
        console.print(f"    [dim]{source.url}[/dim]")


def _render_market_context(market: "Market", research: "MarketResearch") -> None:
    console.print(f"\n[bold]Market:[/bold] {market.title}")
    mid_prob = market.midpoint / 100.0
    console.print(
        f"[dim]Current: {mid_prob:.0%} YES | "
        f"Volume: {market.volume_24h:,} | "
        f"Spread: {market.spread}¢[/dim]\n"
    )

    if research.news:
        _print_market_news(research.news)
    if research.research_papers:
        _print_market_papers(research.research_papers)
    if research.related_coverage:
        _print_market_related(research.related_coverage)

    console.print(f"\n[dim]Cost: ${research.exa_cost_dollars:.4f}[/dim]")


async def _fetch_market(ticker: str) -> "Market":
    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.api.exceptions import KalshiAPIError

    async with KalshiPublicClient() as kalshi:
        try:
            return await kalshi.get_market(ticker)
        except KalshiAPIError as e:
            console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
            raise typer.Exit(1) from None
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None


async def _run_market_context_research(
    market: "Market",
    *,
    max_news: int,
    max_papers: int,
    days: int,
) -> "MarketResearch":
    from kalshi_research.exa import ExaCache, ExaClient
    from kalshi_research.research import MarketContextResearcher

    try:
        async with ExaClient.from_env() as exa:
            cache = ExaCache()
            researcher = MarketContextResearcher(
                exa,
                cache=cache,
                max_news_results=max_news,
                max_paper_results=max_papers,
                news_recency_days=days,
            )
            return await researcher.research_market(market)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("[dim]Set EXA_API_KEY in your environment or .env file.[/dim]")
        raise typer.Exit(1) from None


async def _research_market_context(
    ticker: str,
    *,
    max_news: int,
    max_papers: int,
    days: int,
) -> tuple["Market", "MarketResearch"]:
    market = await _fetch_market(ticker)
    research = await _run_market_context_research(
        market,
        max_news=max_news,
        max_papers=max_papers,
        days=days,
    )
    return market, research


@app.command("context")
def research_context(
    ticker: Annotated[str, typer.Argument(help="Market ticker to research")],
    max_news: Annotated[int, typer.Option("--max-news", help="Max news articles")] = 10,
    max_papers: Annotated[int, typer.Option("--max-papers", help="Max research papers")] = 5,
    days: Annotated[int, typer.Option("--days", help="News recency in days")] = 30,
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Research context for a specific market using Exa."""
    market, research = asyncio.run(
        _research_market_context(ticker, max_news=max_news, max_papers=max_papers, days=days)
    )

    if output_json:
        console.print(json.dumps(asdict(research), indent=2, default=str))
        return

    _render_market_context(market, research)


def _render_topic_research(topic: str, research: "TopicResearch") -> None:
    console.print(f"\n[bold]Topic:[/bold] {topic}\n")

    if research.summary:
        console.print("[bold cyan]📝 Summary[/bold cyan]")
        console.print("─" * 50)
        console.print(research.summary)
        console.print()

        if research.summary_citations:
            console.print("[bold cyan]📚 Citations[/bold cyan]")
            for cite in research.summary_citations:
                console.print(f"  • [link={cite.url}]{cite.title}[/link]")
            console.print()

    if research.articles:
        console.print("[bold cyan]📰 Articles[/bold cyan]")
        console.print("─" * 50)
        for i, source in enumerate(research.articles[:10], 1):
            console.print(f"{i}. [bold]{source.title}[/bold]")
            console.print(f"   [dim]{source.source_domain}[/dim]")
            if source.highlight:
                snippet = source.highlight[:120]
                if len(source.highlight) > 120:
                    snippet += "..."
                console.print(f"   [italic]> {snippet}[/italic]")
            console.print()

    console.print(f"\n[dim]Cost: ${research.exa_cost_dollars:.4f}[/dim]")


async def _run_topic_research(topic: str, *, include_answer: bool) -> "TopicResearch":
    from kalshi_research.exa import ExaCache, ExaClient
    from kalshi_research.research import TopicResearcher

    try:
        async with ExaClient.from_env() as exa:
            cache = ExaCache()
            researcher = TopicResearcher(exa, cache=cache)
            return await researcher.research_topic(topic, include_answer=include_answer)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("[dim]Set EXA_API_KEY in your environment or .env file.[/dim]")
        raise typer.Exit(1) from None


@app.command("topic")
def research_topic(
    topic: Annotated[str, typer.Argument(help="Topic or question to research")],
    no_summary: Annotated[bool, typer.Option("--no-summary", help="Skip LLM summary")] = False,
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Research a topic for thesis ideation using Exa."""
    research = asyncio.run(_run_topic_research(topic, include_answer=not no_summary))

    if output_json:
        console.print(json.dumps(asdict(research), indent=2, default=str))
        return

    _render_topic_research(topic, research)


@app.command("similar")
def research_similar(
    url: Annotated[str, typer.Argument(help="Seed URL to find similar pages for.")],
    num_results: Annotated[
        int,
        typer.Option("--num-results", "-n", help="Number of results."),
    ] = 10,
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Find pages similar to a URL using Exa's /findSimilar endpoint."""
    from kalshi_research.exa import ExaClient
    from kalshi_research.exa.models.similar import FindSimilarResponse

    async def _find() -> FindSimilarResponse:
        try:
            async with ExaClient.from_env() as exa:
                return await exa.find_similar(url, num_results=num_results)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print("[dim]Set EXA_API_KEY in your environment or .env file.[/dim]")
            raise typer.Exit(1) from None

    response = asyncio.run(_find())

    if output_json:
        console.print(
            json.dumps(response.model_dump(by_alias=True, mode="json"), indent=2, default=str),
            markup=False,
        )
        return

    table = Table(title="Exa Similar Pages")
    table.add_column("#", style="dim", justify="right", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("URL", style="cyan")
    table.add_column("Score", style="green", justify="right")

    for i, r in enumerate(response.results[:num_results], start=1):
        score = f"{r.score:.3f}" if isinstance(r.score, float) else ""
        table.add_row(str(i), r.title[:60], r.url[:80], score)

    console.print(table)
    if response.cost_dollars is not None:
        console.print(f"[dim]Cost: ${response.cost_dollars.total:.4f}[/dim]")


@app.command("deep")
def research_deep(
    topic: Annotated[str, typer.Argument(help="Topic or question for deep research.")],
    model: Annotated[
        str,
        typer.Option(
            "--model",
            help="Exa research model tier (exa-research-fast, exa-research, exa-research-pro).",
        ),
    ] = "exa-research",
    wait: Annotated[
        bool,
        typer.Option(
            "--wait",
            help="Wait for completion and print results (incurs additional Exa cost).",
        ),
    ] = False,
    poll_interval: Annotated[
        float,
        typer.Option("--poll-interval", help="Polling interval in seconds (when --wait)."),
    ] = 5.0,
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Timeout in seconds (when --wait)."),
    ] = 300.0,
    output_schema: Annotated[
        Path | None,
        typer.Option("--schema", help="Optional JSON schema file for structured output."),
    ] = None,
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Run Exa async deep research via /research/v1 (paid API)."""
    from kalshi_research.exa import ExaClient
    from kalshi_research.exa.models.research import ResearchTask

    async def _run() -> ResearchTask:
        try:
            schema: dict[str, Any] | None = None
            if output_schema is not None:
                try:
                    schema_raw = json.loads(output_schema.read_text(encoding="utf-8"))
                except OSError as exc:
                    console.print(f"[red]Error:[/red] Failed to read schema file: {exc}")
                    raise typer.Exit(1) from None
                except json.JSONDecodeError as exc:
                    console.print(f"[red]Error:[/red] Schema file is not valid JSON: {exc}")
                    raise typer.Exit(1) from None

                if not isinstance(schema_raw, dict):
                    console.print("[red]Error:[/red] Schema JSON must be an object at the root.")
                    raise typer.Exit(1) from None
                schema = schema_raw

            instructions = (
                "Research the following topic and return key findings with citations:\\n\\n"
                f"{topic.strip()}"
            )
            async with ExaClient.from_env() as exa:
                task = await exa.create_research_task(
                    instructions=instructions,
                    model=model,
                    output_schema=schema,
                )
                if wait:
                    try:
                        task = await exa.wait_for_research(
                            task.research_id,
                            poll_interval=poll_interval,
                            timeout=timeout,
                        )
                    except TimeoutError as exc:
                        console.print(f"[red]Error:[/red] {exc}")
                        raise typer.Exit(1) from None
                return task
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print("[dim]Set EXA_API_KEY in your environment or .env file.[/dim]")
            raise typer.Exit(1) from None

    task = asyncio.run(_run())

    if output_json:
        console.print(
            json.dumps(task.model_dump(by_alias=True, mode="json"), indent=2, default=str),
            markup=False,
        )
        return

    table = Table(title="Exa Research Task")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("research_id", task.research_id)
    table.add_row("status", task.status.value)
    table.add_row("model", str(task.model))
    table.add_row("created_at", str(task.created_at))
    console.print(table)

    if task.output is not None and task.output.content:
        console.print("\n[bold]Output[/bold]")
        console.print(task.output.content)

    if task.cost_dollars is not None:
        console.print(f"\n[dim]Cost: ${task.cost_dollars.total:.4f}[/dim]")
