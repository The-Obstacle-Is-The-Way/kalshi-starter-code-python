"""Typer CLI commands for series discovery."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated

import typer
from rich.table import Table

from kalshi_research.cli.utils import console, exit_kalshi_api_error, run_async

app = typer.Typer(help="Series discovery commands.")

if TYPE_CHECKING:
    from kalshi_research.api.models.series import Series


def _render_series_table(series: Series) -> None:
    table = Table(title=f"Series: {series.ticker}")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Title", series.title)
    table.add_row("Category", series.category)
    table.add_row("Frequency", series.frequency)
    if series.tags:
        table.add_row("Tags", ", ".join(series.tags))
    table.add_row("Fee Type", series.fee_type.value)
    table.add_row("Fee Multiplier", str(series.fee_multiplier))
    if series.volume is not None:
        table.add_row("Volume", f"{series.volume:,}")
    table.add_row("Contract", series.contract_url)
    table.add_row("Terms", series.contract_terms_url)

    sources = series.settlement_sources
    if sources:
        preview = ", ".join((s.url or s.name or "") for s in sources[:3])
        if len(sources) > 3:
            preview += f", … (+{len(sources) - 3})"
        table.add_row("Settlement Sources", preview)

    console.print(table)


@app.command("get")
def series_get(
    ticker: Annotated[str, typer.Argument(help="Series ticker to fetch.")],
    include_volume: Annotated[
        bool,
        typer.Option("--include-volume", help="Include total series volume when available."),
    ] = False,
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """Get series details by ticker."""
    from kalshi_research.api import KalshiPublicClient

    async def _fetch() -> Series:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                return await client.get_series(ticker, include_volume=include_volume)
            except KalshiAPIError as e:
                exit_kalshi_api_error(e)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

    series = run_async(_fetch())

    if output_json:
        typer.echo(json.dumps(series.model_dump(mode="json"), indent=2, default=str))
        return

    _render_series_table(series)
