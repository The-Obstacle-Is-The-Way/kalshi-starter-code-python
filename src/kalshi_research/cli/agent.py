"""CLI commands for research agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, cast
from urllib.parse import urlparse

import typer
from rich.panel import Panel
from rich.table import Table

from kalshi_research.cli.utils import console, exit_kalshi_api_error, run_async
from kalshi_research.constants import DEFAULT_AGENT_MAX_EXA_USD, DEFAULT_AGENT_MAX_LLM_USD
from kalshi_research.exa.policy import ExaMode

if TYPE_CHECKING:
    from kalshi_research.api.models.market import Market

app = typer.Typer(help="Research agent commands")


def _parse_exa_mode(mode: str) -> ExaMode:
    """Parse and validate ExaMode from string, raising typer.Exit on failure."""
    try:
        return ExaMode(mode.lower())
    except ValueError:
        console.print(
            f"[red]Error:[/red] Invalid mode '{mode}'. Expected: fast, standard, or deep."
        )
        raise typer.Exit(1) from None


def _write_json_output(data: dict[str, object], output_file: str | None) -> None:
    """Write JSON output to stdout or file."""
    json_output = json.dumps(data, indent=2, default=str)
    if output_file:
        with Path(output_file).open("w") as f:
            f.write(json_output)
        console.print(f"[green]✓[/green] Results written to {output_file}")
    else:
        typer.echo(json_output)


def _render_research_summary(result: dict[str, object], output_file: str | None) -> None:
    """Render research results in human-readable format."""
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

    _render_factors_table(factors)

    if output_file:
        json_output = json.dumps(result, indent=2, default=str)
        with Path(output_file).open("w") as f:
            f.write(json_output)
        console.print(f"\n[green]✓[/green] Full results written to {output_file}")


def _render_factors_table(factors: list[dict[str, Any]]) -> None:
    """Render factors as a Rich table."""
    if not factors:
        console.print("[yellow]No factors found.[/yellow]")
        return

    table = Table(title="Factors", show_lines=True)
    table.add_column("#", style="cyan", width=3)
    table.add_column("Factor", style="white")
    table.add_column("Source", style="blue")
    table.add_column("Confidence", style="green", width=10)

    for i, factor in enumerate(factors[:10], 1):
        factor_text = factor.get("factor_text", "")
        source_url = factor.get("source_url", "")
        confidence = factor.get("confidence", "unknown")

        if len(factor_text) > 120:
            factor_text = factor_text[:117] + "..."

        domain = urlparse(source_url).netloc.replace("www.", "")
        table.add_row(str(i), factor_text, domain, confidence)

    console.print(table)


async def _execute_analysis(
    ticker: str,
    research_mode: ExaMode,
    max_exa_usd: float,
    max_llm_usd: float,
    quiet: bool,
) -> tuple[dict[str, object], bool]:
    """Execute analysis workflow: fetch market, research, synthesize, verify.

    Returns:
        Tuple of (result dict, is_mock_synthesizer flag)
    """
    from kalshi_research.agent import ResearchAgent
    from kalshi_research.agent.orchestrator import AgentKernel
    from kalshi_research.agent.providers.llm import MockSynthesizer, get_synthesizer
    from kalshi_research.api.exceptions import KalshiAPIError
    from kalshi_research.cli.client_factory import public_client
    from kalshi_research.exa.client import ExaClient
    from kalshi_research.exa.exceptions import ExaAPIError, ExaAuthError

    try:
        async with (
            public_client() as kalshi,
            ExaClient.from_env() as exa,
        ):
            research_agent = ResearchAgent(exa)
            synthesizer = get_synthesizer(max_cost_usd=max_llm_usd)
            is_mock = isinstance(synthesizer, MockSynthesizer)

            if is_mock and not quiet:
                console.print(
                    "[yellow]Warning:[/yellow] Using MockSynthesizer. "
                    "Set KALSHI_SYNTHESIZER_BACKEND=anthropic for real analysis."
                )

            kernel = AgentKernel(
                kalshi_client=kalshi,
                research_agent=research_agent,
                synthesizer=synthesizer,
                max_exa_usd=max_exa_usd,
                max_llm_usd=max_llm_usd,
            )

            if not quiet:
                console.print(f"[cyan]Analyzing {ticker}[/cyan] (mode: {research_mode.value})")

            result = await kernel.analyze(
                ticker=ticker,
                research_mode=research_mode.value,
            )

            output = result.model_dump(mode="json")
            if is_mock:
                output["warning"] = (
                    "MockSynthesizer active. "
                    "Set KALSHI_SYNTHESIZER_BACKEND=anthropic for real analysis."
                )
            return output, is_mock

    except KalshiAPIError as e:
        exit_kalshi_api_error(e)
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


def _render_analysis_human(result: dict[str, object]) -> None:
    """Render analysis result in human-readable format."""
    analysis = cast("dict[str, Any]", result.get("analysis", {}))
    verification = cast("dict[str, Any]", result.get("verification", {}))
    research = cast("dict[str, Any] | None", result.get("research"))

    ticker_val = analysis.get("ticker", "unknown")
    predicted_prob = analysis.get("predicted_prob", 0)
    market_prob = analysis.get("market_prob", 0.0)
    confidence = analysis.get("confidence", "unknown")
    reasoning = analysis.get("reasoning", "")
    total_cost = result.get("total_cost_usd", 0.0)

    passed = verification.get("passed", False)
    issues = verification.get("issues", [])

    console.print(
        Panel(
            f"[bold]Market:[/bold] {ticker_val}\n"
            f"[bold]Predicted:[/bold] {predicted_prob}% (Confidence: {confidence})\n"
            f"[bold]Market Price:[/bold] {market_prob * 100:.1f}%\n"
            f"[bold]Verification:[/bold] {'✓ PASSED' if passed else '✗ FAILED'}\n"
            f"[bold]Total Cost:[/bold] ${total_cost:.3f}",
            title="Analysis Result",
        )
    )

    if reasoning:
        console.print(f"\n[bold]Reasoning:[/bold]\n{reasoning}\n")

    _render_analysis_factors_table(analysis.get("factors", []))

    if not passed:
        console.print("\n[red]Verification Issues:[/red]")
        for issue in issues:
            console.print(f"  • {issue}")

    if research:
        research_cost = research.get("total_cost_usd", 0.0)
        console.print(f"\n[dim]Research cost: ${research_cost:.3f}[/dim]")


def _render_analysis_factors_table(factors: list[dict[str, Any]]) -> None:
    """Render analysis factors as a Rich table."""
    if not factors:
        return

    table = Table(title="Factors", show_lines=True)
    table.add_column("#", style="cyan", width=3)
    table.add_column("Description", style="white")
    table.add_column("Impact", style="yellow", width=10)

    for i, factor in enumerate(factors[:10], 1):
        desc = factor.get("description", "")
        impact = factor.get("impact", "unclear")
        table.add_row(str(i), desc, impact or "unclear")

    console.print(table)


def _output_analysis_json(result: dict[str, object], output_file: str | None, quiet: bool) -> None:
    """Output analysis result as JSON to stdout or file."""
    json_output = json.dumps(result, indent=2, default=str)
    if output_file:
        with Path(output_file).open("w") as f:
            f.write(json_output)
        if not quiet:
            console.print(f"[green]✓[/green] Results written to {output_file}")
    else:
        typer.echo(json_output)


async def _execute_research(
    ticker: str,
    research_mode: ExaMode,
    budget_usd: float | None,
    quiet: bool,
) -> dict[str, object]:
    """Execute research workflow: fetch market from Kalshi, run research via Exa."""
    from kalshi_research.agent import ResearchAgent
    from kalshi_research.api.exceptions import KalshiAPIError
    from kalshi_research.cli.client_factory import public_client
    from kalshi_research.exa.client import ExaClient
    from kalshi_research.exa.exceptions import ExaAPIError, ExaAuthError

    async with public_client() as kalshi:
        try:
            market: Market = await kalshi.get_market(ticker)
        except KalshiAPIError as e:
            exit_kalshi_api_error(e)

    try:
        async with ExaClient.from_env() as exa:
            agent = ResearchAgent(exa)

            if not quiet:
                console.print(f"[cyan]Researching {ticker}[/cyan] (mode: {research_mode.value})")

            summary = await agent.research(market, mode=research_mode, budget_usd=budget_usd)
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


@app.command()
def research(
    ticker: Annotated[str, typer.Argument(help="Market ticker to research")],
    mode: Annotated[
        str,
        typer.Option("--mode", "-m", help="Research mode (fast, standard, deep)"),
    ] = "standard",
    budget_usd: Annotated[
        float | None,
        typer.Option(
            "--budget-usd", "-b", help="Budget limit in USD (uses mode default if not specified)"
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
    research_mode = _parse_exa_mode(mode)
    result = run_async(_execute_research(ticker, research_mode, budget_usd, quiet=output_json))

    if output_json:
        _write_json_output(result, output_file)
    else:
        _render_research_summary(result, output_file)


@app.command()
def analyze(
    ticker: Annotated[str, typer.Argument(help="Market ticker to analyze")],
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            "-m",
            help="Research mode (fast, standard, deep)",
        ),
    ] = "standard",
    max_exa_usd: Annotated[
        float,
        typer.Option("--max-exa-usd", help="Maximum Exa budget per run"),
    ] = DEFAULT_AGENT_MAX_EXA_USD,
    max_llm_usd: Annotated[
        float,
        typer.Option("--max-llm-usd", help="Maximum LLM budget per run (Phase 2)"),
    ] = DEFAULT_AGENT_MAX_LLM_USD,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON (default)"),
    ] = True,
    output_file: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Write output to file"),
    ] = None,
    human: Annotated[
        bool,
        typer.Option("--human", help="Human-readable output instead of JSON"),
    ] = False,
) -> None:
    """
    Run complete agent analysis workflow for a market.

    Executes the full orchestration:
    1. Fetch market info + orderbook (Kalshi)
    2. Gather evidence (Exa Research Agent)
    3. Synthesize probability estimate (LLM)
    4. Verify output (rule-based)

    Examples:
        kalshi agent analyze INXD-25FEB28
        kalshi agent analyze INXD-25FEB28 --mode deep --max-exa-usd 0.50
        kalshi agent analyze INXD-25FEB28 --human
        kalshi agent analyze INXD-25FEB28 --output result.json
    """
    research_mode = _parse_exa_mode(mode)

    # Determine quiet mode: suppress progress output for JSON-only output
    quiet = output_json and not human

    result, _ = run_async(_execute_analysis(ticker, research_mode, max_exa_usd, max_llm_usd, quiet))

    if human:
        _render_analysis_human(result)
    else:
        _output_analysis_json(result, output_file, quiet)
