"""Render helper functions for thesis CLI commands."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.table import Table

from kalshi_research.cli.utils import console

if TYPE_CHECKING:
    from kalshi_research.research.invalidation import InvalidationSeverity, InvalidationSignal


def _print_invalidation_signals(
    signals: "list[InvalidationSignal]", *, severity_enum: "type[InvalidationSeverity]"
) -> None:
    """Print invalidation signals with severity-based formatting."""
    console.print("[yellow]⚠️ Potential Invalidation Signals[/yellow]")
    console.print("─" * 50)

    for signal in signals:
        severity = signal.severity
        label = severity.value.upper()
        color = (
            "red"
            if severity == severity_enum.HIGH
            else "yellow"
            if severity == severity_enum.MEDIUM
            else "white"
        )
        console.print(f"[{color}][{label}][/{color}] {signal.title}")
        console.print(f"  [dim]{signal.source_domain} | {signal.url}[/dim]")
        if signal.reason:
            console.print(f"  [dim]{signal.reason}[/dim]")
        if signal.snippet:
            console.print(f"  [italic]> {signal.snippet[:200]}[/italic]")
        console.print()


def _find_thesis_by_id(theses: list[dict[str, Any]], thesis_id: str) -> dict[str, Any] | None:
    """Find a thesis by ID prefix match."""
    for t in theses:
        if t["id"].startswith(thesis_id):
            return t
    return None


def _render_thesis_header(thesis: dict[str, Any]) -> None:
    """Render thesis header (title, ID, status)."""
    console.print(f"\n[bold]{thesis['title']}[/bold]")
    console.print(f"[dim]ID: {thesis['id']}[/dim]")
    console.print(f"[dim]Status: {thesis['status']}[/dim]\n")


def _render_thesis_fields_table(thesis: dict[str, Any]) -> None:
    """Render thesis fields as a table."""
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


def _render_thesis_cases_and_updates(thesis: dict[str, Any]) -> None:
    """Render bull/bear cases, updates, and research summary."""
    console.print(f"\n[cyan]Bull Case:[/cyan] {thesis['bull_case']}")
    console.print(f"[cyan]Bear Case:[/cyan] {thesis['bear_case']}")

    if thesis["updates"]:
        console.print("\n[cyan]Updates:[/cyan]")
        for update in thesis["updates"]:
            console.print(f"  {update['timestamp']}: {update['note']}")

    if thesis.get("research_summary"):
        console.print("\n[cyan]Research Summary:[/cyan]")
        console.print(thesis["research_summary"])


def _render_thesis_evidence(evidence: list[dict[str, Any]]) -> None:
    """Render evidence groups (bull, bear, neutral)."""
    if not evidence:
        return

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


async def _fetch_and_render_linked_positions(thesis_id: str, db_path: Path) -> None:
    """Fetch and render positions linked to a thesis."""
    from sqlalchemy import select

    from kalshi_research.cli.db import open_db_session
    from kalshi_research.portfolio import Position

    async with open_db_session(db_path) as session:
        query = select(Position).where(Position.thesis_id == thesis_id)
        result = await session.execute(query)
        positions = result.scalars().all()

        if not positions:
            console.print("\n[dim]No positions linked to this thesis.[/dim]")
            return

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
