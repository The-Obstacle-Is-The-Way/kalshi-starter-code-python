"""Typer CLI command for topic research."""

import json
from dataclasses import asdict
from typing import TYPE_CHECKING, Annotated

import typer

from kalshi_research.cli.utils import console, run_async
from kalshi_research.exa.policy import ExaMode, ExaPolicy

if TYPE_CHECKING:
    from kalshi_research.research.topic import TopicResearch


def _render_topic_research(topic: str, research: "TopicResearch") -> None:
    """Render topic research results."""
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
    if research.budget_exhausted:
        console.print(
            f"[yellow]Budget exhausted[/yellow] "
            f"(${research.budget_spent_usd:.4f} / ${research.budget_usd:.2f}); "
            "results may be partial."
        )


async def _run_topic_research(
    topic: str,
    *,
    include_answer: bool,
    mode: ExaMode,
    budget_usd: float | None,
) -> "TopicResearch":
    """Run Exa-backed topic research for thesis ideation.

    Args:
        topic: Topic or question to research.
        include_answer: Whether to request an LLM answer/summary.
        mode: Exa policy mode.
        budget_usd: Optional budget limit.

    Returns:
        The `TopicResearch` result from `TopicResearcher`.

    Raises:
        typer.Exit: If Exa configuration is missing/invalid.
    """
    from kalshi_research.exa import ExaCache, ExaClient
    from kalshi_research.research import TopicResearcher

    try:
        async with ExaClient.from_env() as exa:
            cache = ExaCache()
            policy = ExaPolicy.from_mode(mode=mode, budget_usd=budget_usd)
            researcher = TopicResearcher(exa, cache=cache, policy=policy)
            return await researcher.research_topic(topic, include_answer=include_answer)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("[dim]Check EXA_API_KEY and --budget-usd (must be > 0).[/dim]")
        raise typer.Exit(1) from None


def research_topic(
    topic: Annotated[str, typer.Argument(help="Topic or question to research")],
    no_summary: Annotated[bool, typer.Option("--no-summary", help="Skip LLM summary")] = False,
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
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Research a topic for thesis ideation using Exa."""
    if mode == ExaMode.FAST and not no_summary:
        console.print("[dim]Note: --mode fast disables LLM summary output (retrieve-only).[/dim]")

    research = run_async(
        _run_topic_research(
            topic,
            include_answer=not no_summary,
            mode=mode,
            budget_usd=budget_usd,
        )
    )

    if output_json:
        typer.echo(json.dumps(asdict(research), indent=2, default=str))
        return

    _render_topic_research(topic, research)
