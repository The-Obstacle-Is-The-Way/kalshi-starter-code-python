"""Typer CLI command for thesis suggestion via Exa research."""

from typing import Annotated

import typer

from kalshi_research.cli.utils import console, print_budget_exhausted, run_async
from kalshi_research.exa.policy import ExaMode


def research_thesis_suggest(
    category: Annotated[
        str | None,
        typer.Option("--category", "-c", help="Optional category filter (crypto, politics, etc.)"),
    ] = None,
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
    """Generate thesis ideas from Exa research."""
    from kalshi_research.exa import ExaClient
    from kalshi_research.exa.policy import ExaPolicy
    from kalshi_research.research.thesis_research import ThesisSuggester

    async def _suggest() -> None:
        try:
            async with ExaClient.from_env() as exa:
                policy = ExaPolicy.from_mode(mode=mode, budget_usd=budget_usd)
                suggester = ThesisSuggester(exa, policy=policy)
                suggestions = await suggester.suggest_theses(category=category)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print("[dim]Check EXA_API_KEY and --budget-usd (must be > 0).[/dim]")
            raise typer.Exit(1) from None

        if not suggestions:
            console.print("[yellow]No suggestions found.[/yellow]")
            print_budget_exhausted(suggester)
            return

        console.print("\n[bold]🎯 Thesis Suggestions Based on Research[/bold]")
        console.print("─" * 60)
        for i, s in enumerate(suggestions, 1):
            console.print(f"\n[bold]{i}. {s.suggested_thesis}[/bold]")
            console.print(f"[dim]Source:[/dim] {s.source_title} ({s.source_url})")
            if s.key_insight:
                console.print(f"[italic]> {s.key_insight[:200]}[/italic]")
        print_budget_exhausted(suggester)

    run_async(_suggest())
