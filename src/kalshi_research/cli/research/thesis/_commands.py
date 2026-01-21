"""Typer CLI command implementations for thesis management."""

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.table import Table

from kalshi_research.cli.research._shared import (
    _get_thesis_file,
    _load_theses,
    _resolve_thesis,
    _save_theses,
    _serialize_thesis_evidence,
)
from kalshi_research.cli.research.thesis._helpers import (
    _fetch_and_render_linked_positions,
    _find_thesis_by_id,
    _print_invalidation_signals,
    _render_thesis_cases_and_updates,
    _render_thesis_evidence,
    _render_thesis_fields_table,
    _render_thesis_header,
)
from kalshi_research.cli.utils import console, print_budget_exhausted, run_async
from kalshi_research.exa.policy import ExaMode, ExaPolicy
from kalshi_research.paths import DEFAULT_DB_PATH

if TYPE_CHECKING:
    from kalshi_research.research.invalidation import InvalidationReport
    from kalshi_research.research.thesis import Thesis as ThesisModel
    from kalshi_research.research.thesis_research import ResearchedThesisData


async def _check_thesis_invalidation(
    thesis_id: str,
    *,
    hours: int,
    mode: ExaMode,
    budget_usd: float | None,
) -> tuple["ThesisModel", "InvalidationReport", object]:
    """Check a thesis for invalidation signals via Exa research."""
    from kalshi_research.exa import ExaClient
    from kalshi_research.research.invalidation import InvalidationDetector
    from kalshi_research.research.thesis import ThesisTracker

    tracker = ThesisTracker(_get_thesis_file())
    thesis = _resolve_thesis(tracker, thesis_id)
    if thesis is None:
        raise KeyError(thesis_id)

    policy = ExaPolicy.from_mode(mode=mode, budget_usd=budget_usd)
    async with ExaClient.from_env() as exa:
        detector = InvalidationDetector(exa, lookback_hours=hours, policy=policy)
        report = await detector.check_thesis(thesis)
    return thesis, report, detector


async def _gather_thesis_research_data(
    market_ticker: str,
    *,
    thesis_direction: str,
    mode: ExaMode,
    budget_usd: float | None,
) -> "ResearchedThesisData":
    """Gather research data for a new thesis via Exa."""
    from kalshi_research.cli.research._shared import _fetch_market
    from kalshi_research.exa import ExaClient
    from kalshi_research.exa.policy import ExaPolicy
    from kalshi_research.research.thesis_research import ThesisResearcher

    market = await _fetch_market(market_ticker)
    async with ExaClient.from_env() as exa:
        policy = ExaPolicy.from_mode(mode=mode, budget_usd=budget_usd)
        researcher = ThesisResearcher(exa, policy=policy)
        return await researcher.research_for_thesis(market, thesis_direction=thesis_direction)


def _handle_thesis_research(
    market_ticker: str,
    your_prob: float,
    mode: ExaMode,
    budget_usd: float | None,
    yes: bool,
    bull_case: str,
    bear_case: str,
) -> tuple[str, str, list[dict[str, Any]], str | None, str | None]:
    """Handle optional research for thesis creation.

    Returns:
        Tuple of (final_bull, final_bear, evidence, research_summary, last_research_at)
    """
    console.print("[dim]🔍 Researching thesis...[/dim]")
    try:
        direction = "yes" if your_prob > 0.5 else "no"
        research_data = run_async(
            _gather_thesis_research_data(
                market_ticker, thesis_direction=direction, mode=mode, budget_usd=budget_usd
            )
        )
    except ValueError as e:
        console.print(f"[yellow]Research skipped:[/yellow] {e}")
        return bull_case, bear_case, [], None, None

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

    final_bull, final_bear = bull_case, bear_case
    if yes or typer.confirm("Accept these suggestions?", default=True):
        final_bull = research_data.suggested_bull_case
        final_bear = research_data.suggested_bear_case

    evidence = _serialize_thesis_evidence(
        research_data.bull_evidence + research_data.bear_evidence + research_data.neutral_evidence
    )
    last_research_at = datetime.now(UTC).isoformat() if evidence else None
    console.print(
        f"[dim]Research cost: ${research_data.budget_spent_usd:.4f}[/dim]"
        f" ([dim]budget: ${research_data.budget_usd:.2f}[/dim])"
    )
    if research_data.budget_exhausted:
        console.print(
            f"[yellow]Budget exhausted[/yellow] "
            f"(${research_data.budget_spent_usd:.4f} / ${research_data.budget_usd:.2f}); "
            "results may be partial."
        )
    return final_bull, final_bear, evidence, research_data.summary, last_research_at


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
    mode: Annotated[
        ExaMode,
        typer.Option("--mode", help="Exa policy mode: fast (cheap), standard, deep (expensive)."),
    ] = ExaMode.STANDARD,
    budget_usd: Annotated[
        float | None,
        typer.Option(
            "--budget-usd",
            help="Max Exa spend (USD) for this command. Default depends on mode.",
        ),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Accept research suggestions without prompting (only with --with-research).",
        ),
    ] = False,
) -> None:
    """Create a new research thesis."""
    thesis_id = str(uuid.uuid4())
    market_tickers = [t.strip() for t in markets.split(",") if t.strip()]
    evidence: list[dict[str, Any]] = []
    final_bull, final_bear, research_summary, last_research_at = (
        bull_case,
        bear_case,
        None,
        None,
    )

    if with_research and market_tickers:
        final_bull, final_bear, evidence, research_summary, last_research_at = (
            _handle_thesis_research(
                market_tickers[0], your_prob, mode, budget_usd, yes, bull_case, bear_case
            )
        )

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


def research_thesis_show(
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

    thesis = _find_thesis_by_id(theses, thesis_id)
    if not thesis:
        console.print(f"[red]Error:[/red] Thesis not found: {thesis_id}")
        raise typer.Exit(2)

    _render_thesis_header(thesis)
    _render_thesis_fields_table(thesis)
    _render_thesis_cases_and_updates(thesis)

    evidence = thesis.get("evidence") or []
    if isinstance(evidence, list):
        _render_thesis_evidence(evidence)

    if with_positions:
        run_async(_fetch_and_render_linked_positions(thesis["id"], db_path))


def research_thesis_edit(
    thesis_id: Annotated[str, typer.Argument(help="Thesis ID to edit")],
    title: Annotated[str | None, typer.Option("--title", help="Update thesis title")] = None,
    bull_case: Annotated[str | None, typer.Option("--bull", help="Update bull case")] = None,
    bear_case: Annotated[str | None, typer.Option("--bear", help="Update bear case")] = None,
) -> None:
    """Edit a thesis stored in the local thesis file."""
    if title is None and bull_case is None and bear_case is None:
        console.print("[red]Error:[/red] No changes specified.")
        raise typer.Exit(1)

    data = _load_theses()
    theses = data.get("theses", [])

    for thesis in theses:
        if thesis.get("id", "").startswith(thesis_id):
            if title is not None:
                thesis["title"] = title
            if bull_case is not None:
                thesis["bull_case"] = bull_case
            if bear_case is not None:
                thesis["bear_case"] = bear_case

            _save_theses(data)
            console.print(
                f"[green]✓[/green] Thesis updated: {thesis.get('title', '(missing title)')}"
            )
            console.print(f"[dim]ID: {thesis.get('id', '')[:8]}[/dim]")
            return

    console.print(f"[red]Error:[/red] Thesis not found: {thesis_id}")
    raise typer.Exit(2)


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

    console.print(f"[red]Error:[/red] Thesis not found: {thesis_id}")
    raise typer.Exit(2)


def research_thesis_check_invalidation(
    thesis_id: Annotated[str, typer.Argument(help="Thesis ID to check")],
    hours: Annotated[int, typer.Option("--hours", "-h", help="Lookback hours")] = 48,
    mode: Annotated[
        ExaMode,
        typer.Option("--mode", help="Exa policy mode: fast (cheap), standard, deep (expensive)."),
    ] = ExaMode.STANDARD,
    budget_usd: Annotated[
        float | None,
        typer.Option(
            "--budget-usd",
            help="Max Exa spend (USD) for this command. Default depends on mode.",
        ),
    ] = None,
) -> None:
    """Check for signals that might invalidate your thesis."""
    from kalshi_research.research.invalidation import InvalidationSeverity

    try:
        thesis, report, detector = run_async(
            _check_thesis_invalidation(
                thesis_id,
                hours=hours,
                mode=mode,
                budget_usd=budget_usd,
            )
        )
    except KeyError:
        console.print(f"[red]Error:[/red] Thesis not found: {thesis_id}")
        raise typer.Exit(2) from None
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("[dim]Check EXA_API_KEY and --budget-usd (must be > 0).[/dim]")
        raise typer.Exit(1) from None

    console.print(f"\n[bold]Thesis:[/bold] {thesis.title}")
    console.print(f"Your probability: {thesis.your_probability:.0%} YES")
    console.print(f"[dim]Checking last {hours} hours...[/dim]\n")

    if not report.signals:
        console.print("[green]✓ No invalidation signals found[/green]")
        console.print(f"[dim]{report.recommendation}[/dim]")
        print_budget_exhausted(detector)
        return

    _print_invalidation_signals(report.signals, severity_enum=InvalidationSeverity)
    if report.recommendation:
        console.print(f"[bold]Recommendation:[/bold] {report.recommendation}")
    print_budget_exhausted(detector)
