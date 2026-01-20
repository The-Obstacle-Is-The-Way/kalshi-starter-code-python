"""Typer CLI command for market context research."""

import json
from dataclasses import asdict
from typing import TYPE_CHECKING, Annotated

import typer

from kalshi_research.cli.research._shared import _fetch_market
from kalshi_research.cli.utils import console, run_async
from kalshi_research.exa.policy import ExaMode, ExaPolicy

if TYPE_CHECKING:
    from kalshi_research.api.models.market import Market
    from kalshi_research.research.context import MarketResearch, ResearchSource


def _print_market_news(sources: "list[ResearchSource]") -> None:
    """Print news sources section."""
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


def _print_market_papers(sources: "list[ResearchSource]") -> None:
    """Print research papers section."""
    console.print("[bold cyan]📄 Research Papers[/bold cyan]")
    console.print("─" * 40)
    for i, source in enumerate(sources[:3], 1):
        console.print(f"{i}. [bold]{source.title}[/bold]")
        console.print(f"   [dim]Source: {source.source_domain}[/dim]")
        console.print()


def _print_market_related(sources: "list[ResearchSource]") -> None:
    """Print related coverage section."""
    console.print("[bold cyan]🔗 Related Coverage[/bold cyan]")
    console.print("─" * 40)
    for source in sources[:3]:
        console.print(f"  • {source.title}")
        console.print(f"    [dim]{source.url}[/dim]")


def _render_market_context(market: "Market", research: "MarketResearch") -> None:
    """Render market context research results."""
    console.print(f"\n[bold]Market:[/bold] {market.title}")
    midpoint = market.midpoint
    spread = market.spread
    mid_prob = (midpoint / 100.0) if midpoint is not None else None
    mid_display = f"{mid_prob:.0%} YES" if mid_prob is not None else "N/A"
    spread_display = f"{spread}¢" if spread is not None else "N/A"
    console.print(
        f"[dim]Current: {mid_display} | "
        f"Volume: {market.volume_24h:,} | "
        f"Spread: {spread_display}[/dim]\n"
    )

    if research.news:
        _print_market_news(research.news)
    if research.research_papers:
        _print_market_papers(research.research_papers)
    if research.related_coverage:
        _print_market_related(research.related_coverage)

    console.print(f"\n[dim]Cost: ${research.exa_cost_dollars:.4f}[/dim]")
    if research.budget_exhausted:
        console.print(
            f"[yellow]Budget exhausted[/yellow] "
            f"(${research.budget_spent_usd:.4f} / ${research.budget_usd:.2f}); "
            "results may be partial."
        )


async def _run_market_context_research(
    market: "Market",
    *,
    max_news: int,
    max_papers: int,
    days: int,
    mode: ExaMode,
    budget_usd: float | None,
) -> "MarketResearch":
    """Run Exa-backed market context research for a given market.

    Args:
        market: Market to research.
        max_news: Maximum number of news sources to retrieve.
        max_papers: Maximum number of research-paper sources to retrieve.
        days: Recency window for news results (days).
        mode: Exa policy mode.
        budget_usd: Optional budget limit.

    Returns:
        The `MarketResearch` result from `MarketContextResearcher`.

    Raises:
        typer.Exit: If Exa configuration is missing/invalid.
    """
    from kalshi_research.exa import ExaCache, ExaClient
    from kalshi_research.research import MarketContextResearcher

    try:
        async with ExaClient.from_env() as exa:
            cache = ExaCache()
            policy = ExaPolicy.from_mode(mode=mode, budget_usd=budget_usd)
            researcher = MarketContextResearcher(
                exa,
                cache=cache,
                max_news_results=max_news,
                max_paper_results=max_papers,
                news_recency_days=days,
                policy=policy,
            )
            return await researcher.research_market(market)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("[dim]Check EXA_API_KEY and --budget-usd (must be > 0).[/dim]")
        raise typer.Exit(1) from None


async def _research_market_context(
    ticker: str,
    *,
    max_news: int,
    max_papers: int,
    days: int,
    mode: ExaMode,
    budget_usd: float | None,
) -> tuple["Market", "MarketResearch"]:
    """Fetch market and run context research."""
    market = await _fetch_market(ticker)
    research = await _run_market_context_research(
        market,
        max_news=max_news,
        max_papers=max_papers,
        days=days,
        mode=mode,
        budget_usd=budget_usd,
    )
    return market, research


def research_context(
    ticker: Annotated[str, typer.Argument(help="Market ticker to research")],
    max_news: Annotated[int, typer.Option("--max-news", help="Max news articles")] = 10,
    max_papers: Annotated[int, typer.Option("--max-papers", help="Max research papers")] = 5,
    days: Annotated[int, typer.Option("--days", help="News recency in days")] = 30,
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
    """Research context for a specific market using Exa."""
    market, research = run_async(
        _research_market_context(
            ticker,
            max_news=max_news,
            max_papers=max_papers,
            days=days,
            mode=mode,
            budget_usd=budget_usd,
        )
    )

    if output_json:
        typer.echo(json.dumps(asdict(research), indent=2, default=str))
        return

    _render_market_context(market, research)
