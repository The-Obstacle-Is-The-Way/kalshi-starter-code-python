"""CLI commands for research agent."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer

from kalshi_research.cli.utils import console
from kalshi_research.exa.policy import ExaMode

app = typer.Typer(help="Research agent commands")


@app.command()
def research(  # noqa: PLR0915
    ticker: Annotated[str, typer.Argument(help="Market ticker to research")],
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            "-m",
            help="Research mode (fast, standard, deep)",
        ),
    ] = "standard",
    budget_usd: Annotated[
        float | None,
        typer.Option(
            "--budget-usd",
            "-b",
            help="Budget limit in USD (uses mode default if not specified)",
        ),
    ] = None,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
    output_file: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Write output to file"),
    ] = None,
) -> None:
    """
    Run research agent for a market ticker.

    Examples:
        kalshi agent research INXD-25FEB28 --mode fast
        kalshi agent research INXD-25FEB28 --mode deep --budget-usd 1.0 --json
        kalshi agent research INXD-25FEB28 --json --output report.json
    """
    from kalshi_research.agent import ResearchAgent
    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.exa.client import ExaClient

    # Parse mode
    try:
        research_mode = ExaMode(mode.lower())
    except ValueError:
        console.print(
            f"[red]Error:[/red] Invalid mode '{mode}'. Expected: fast, standard, or deep."
        )
        raise typer.Exit(1) from None

    async def _run() -> dict[str, object]:
        from kalshi_research.api.exceptions import KalshiAPIError
        from kalshi_research.exa.exceptions import ExaAPIError, ExaAuthError

        # Fetch market
        async with KalshiPublicClient() as kalshi:
            try:
                market = await kalshi.get_market(ticker)
            except KalshiAPIError as e:
                console.print(f"[red]Kalshi API Error {e.status_code}:[/red] {e.message}")
                raise typer.Exit(1) from None

        # Run research
        try:
            async with ExaClient.from_env() as exa:
                agent = ResearchAgent(exa)

                if not output_json:
                    console.print(
                        f"[cyan]Researching {ticker}[/cyan] (mode: {research_mode.value})"
                    )

                summary = await agent.research(
                    market,
                    mode=research_mode,
                    budget_usd=budget_usd,
                )

                return summary.model_dump(mode="json")

        except ExaAuthError as e:
            console.print(f"[red]Exa Auth Error:[/red] {e}")
            console.print("[yellow]Hint:[/yellow] Check your EXA_API_KEY environment variable")
            raise typer.Exit(1) from None
        except ExaAPIError as e:
            console.print(f"[red]Exa API Error:[/red] {e}")
            raise typer.Exit(1) from None
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

    result = asyncio.run(_run())

    # Output handling
    if output_json:
        json_output = json.dumps(result, indent=2, default=str)
        if output_file:
            with Path(output_file).open("w") as f:
                f.write(json_output)
            console.print(f"[green]✓[/green] Results written to {output_file}")
        else:
            console.print(json_output)
    else:
        # Human-readable output
        from typing import Any, cast

        from rich.panel import Panel
        from rich.table import Table

        ticker_val = result.get("ticker", "unknown")
        title = result.get("title", "")
        mode_val = result.get("mode", "unknown")
        cost = result.get("total_cost_usd", 0.0)
        budget = result.get("budget_usd", 0.0)
        budget_exhausted = result.get("budget_exhausted", False)
        factors = cast("list[dict[str, Any]]", result.get("factors", []))

        console.print(
            Panel(
                f"[bold]{title}[/bold]\n"
                f"Ticker: {ticker_val} | Mode: {mode_val}\n"
                f"Cost: ${cost:.3f} / ${budget:.2f}"
                + (" [red](budget exhausted)[/red]" if budget_exhausted else ""),
                title="Research Summary",
            )
        )

        if factors:
            table = Table(title="Factors", show_lines=True)
            table.add_column("#", style="cyan", width=3)
            table.add_column("Factor", style="white")
            table.add_column("Source", style="blue")
            table.add_column("Confidence", style="green", width=10)

            for i, factor in enumerate(factors[:10], 1):
                factor_text = factor.get("factor_text", "")
                source_url = factor.get("source_url", "")
                confidence = factor.get("confidence", "unknown")

                # Truncate long factor text
                if len(factor_text) > 120:
                    factor_text = factor_text[:117] + "..."

                # Show domain only for source
                from urllib.parse import urlparse

                domain = urlparse(source_url).netloc.replace("www.", "")

                table.add_row(str(i), factor_text, domain, confidence)

            console.print(table)
        else:
            console.print("[yellow]No factors found.[/yellow]")

        if output_file:
            json_output = json.dumps(result, indent=2, default=str)
            with Path(output_file).open("w") as f:
                f.write(json_output)
            console.print(f"\n[green]✓[/green] Full results written to {output_file}")
