"""Typer CLI command for similar page search."""

import json
from typing import Annotated

import typer
from rich.table import Table

from kalshi_research.cli.utils import console, run_async
from kalshi_research.exa.policy import ExaBudget, ExaMode, ExaPolicy


def research_similar(
    url: Annotated[str, typer.Argument(help="Seed URL to find similar pages for.")],
    num_results: Annotated[
        int,
        typer.Option("--num-results", "-n", help="Number of results."),
    ] = 10,
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
    """Find pages similar to a URL using Exa's /findSimilar endpoint."""
    from kalshi_research.exa import ExaClient
    from kalshi_research.exa.models.similar import FindSimilarResponse
    from kalshi_research.exa.policy import extract_exa_cost_total

    async def _find() -> FindSimilarResponse:
        try:
            policy = ExaPolicy.from_mode(mode=mode, budget_usd=budget_usd)
            budget = ExaBudget(limit_usd=policy.budget_usd)
            estimated_cost = policy.estimate_find_similar_cost_usd(
                num_results=num_results,
                include_text=False,
                include_highlights=False,
            )
            if not budget.can_spend(estimated_cost):
                console.print(
                    "[yellow]Budget exhausted[/yellow] "
                    f"(estimated ${estimated_cost:.4f} > "
                    f"remaining ${budget.remaining_usd:.4f} of ${budget.limit_usd:.2f})."
                )
                raise typer.Exit(1)

            async with ExaClient.from_env() as exa:
                response = await exa.find_similar(url, num_results=num_results)
                budget.record_spend(extract_exa_cost_total(response))
                return response
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print("[dim]Check EXA_API_KEY and --budget-usd (must be > 0).[/dim]")
            raise typer.Exit(1) from None

    response = run_async(_find())

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
