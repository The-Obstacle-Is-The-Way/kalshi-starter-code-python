"""Typer CLI command for deep research via Exa /research/v1 API."""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.table import Table

from kalshi_research.cli.utils import console, run_async

if TYPE_CHECKING:
    from kalshi_research.exa.models.research import ResearchTask


def _load_research_output_schema(output_schema: Path | None) -> dict[str, Any] | None:
    """Load and validate JSON schema from file."""
    if output_schema is None:
        return None

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

    return schema_raw


async def _run_deep_research(
    topic: str,
    *,
    model: str,
    wait: bool,
    poll_interval: float,
    timeout: float,
    output_schema: Path | None,
) -> "ResearchTask":
    """Create an Exa research task and optionally wait for completion.

    Args:
        topic: Topic/question to include in the research instructions.
        model: Exa research model tier to use.
        wait: If true, poll until the task completes (incurs additional cost).
        poll_interval: Polling interval in seconds when waiting.
        timeout: Timeout in seconds when waiting.
        output_schema: Optional JSON schema file to request structured output.

    Returns:
        The created (or completed) `ResearchTask`.

    Raises:
        typer.Exit: If Exa configuration is missing/invalid, or waiting times out.
    """
    from kalshi_research.exa import ExaClient

    schema = _load_research_output_schema(output_schema)
    instructions = (
        f"Research the following topic and return key findings with citations:\n\n{topic.strip()}"
    )

    try:
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
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        console.print("[dim]Set EXA_API_KEY in your environment or .env file.[/dim]")
        raise typer.Exit(1) from None


def research_deep(
    topic: Annotated[str, typer.Argument(help="Topic or question for deep research.")],
    model: Annotated[
        str,
        typer.Option(
            "--model",
            help=("Exa research model tier (exa-research-fast, exa-research, exa-research-pro)."),
        ),
    ] = "exa-research",
    budget_usd: Annotated[
        float | None,
        typer.Option(
            "--budget-usd",
            help=(
                "Optional cost ceiling (USD). Exa /research tasks do not support server-side "
                "budget limits; this is used to warn if the completed task exceeds your budget."
            ),
        ),
    ] = None,
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
    if budget_usd is not None and budget_usd <= 0:
        console.print("[red]Error:[/red] budget_usd must be positive")
        raise typer.Exit(1)

    try:
        task = run_async(
            _run_deep_research(
                topic,
                model=model,
                wait=wait,
                poll_interval=poll_interval,
                timeout=timeout,
                output_schema=output_schema,
            )
        )
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None

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
        if budget_usd is not None and task.cost_dollars.total > budget_usd:
            console.print(
                f"[yellow]Warning:[/yellow] Cost exceeded budget "
                f"(${task.cost_dollars.total:.4f} > ${budget_usd:.2f})."
            )
