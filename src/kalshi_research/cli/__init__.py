"""
CLI application for Kalshi Research Platform.

Provides commands for data collection, analysis, and research.
"""

from __future__ import annotations

from typing import Annotated

import typer
from dotenv import find_dotenv, load_dotenv

from kalshi_research.cli.alerts import app as alerts_app
from kalshi_research.cli.analysis import app as analysis_app
from kalshi_research.cli.data import app as data_app
from kalshi_research.cli.market import app as market_app
from kalshi_research.cli.news import app as news_app
from kalshi_research.cli.portfolio import app as portfolio_app
from kalshi_research.cli.research import app as research_app
from kalshi_research.cli.scan import app as scan_app
from kalshi_research.cli.utils import console

app = typer.Typer(
    name="kalshi",
    help="Kalshi Research Platform CLI - Tools for prediction market research.",
    add_completion=False,
)

app.add_typer(data_app, name="data")
app.add_typer(market_app, name="market")
app.add_typer(scan_app, name="scan")
app.add_typer(alerts_app, name="alerts")
app.add_typer(analysis_app, name="analysis")
app.add_typer(research_app, name="research")
app.add_typer(portfolio_app, name="portfolio")
app.add_typer(news_app, name="news")


@app.callback()
def main(
    environment: Annotated[
        str | None,
        typer.Option(
            "--env",
            "-e",
            help="API environment (prod/demo). Defaults to KALSHI_ENVIRONMENT or prod.",
            show_default=False,
        ),
    ] = None,
) -> None:
    """Kalshi Research Platform CLI."""
    import os

    from kalshi_research.api.config import Environment, set_environment

    load_dotenv(find_dotenv(usecwd=True))

    # Priority: CLI flag > KALSHI_ENVIRONMENT env var > default "prod"
    env_var = os.getenv("KALSHI_ENVIRONMENT")

    try:
        final_env = (environment or env_var or "prod").strip().lower()
        set_environment(Environment(final_env))
    except ValueError:
        console.print(
            f"[red]Error:[/red] Invalid environment '{environment or env_var}'. "
            "Expected 'prod' or 'demo'."
        )
        raise typer.Exit(1) from None


@app.command()
def version() -> None:
    """Show version information."""
    from kalshi_research import __version__

    console.print(f"kalshi-research v{__version__}")


@app.command()
def status(
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Show Kalshi exchange operational status."""
    import asyncio
    import json

    from rich.table import Table

    from kalshi_research.api import KalshiPublicClient

    async def _fetch() -> dict[str, object]:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                status = await client.get_exchange_status()
            except KalshiAPIError as e:
                console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
                raise typer.Exit(1) from None
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None
        if not isinstance(status, dict):
            console.print("[red]Error:[/red] Unexpected exchange status response type")
            raise typer.Exit(1) from None
        return status

    status = asyncio.run(_fetch())

    if output_json:
        console.print(json.dumps(status, indent=2, default=str))
        return

    table = Table(title="Exchange Status")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    exchange_active = status.get("exchange_active")
    trading_active = status.get("trading_active")
    table.add_row("exchange_active", str(exchange_active))
    table.add_row("trading_active", str(trading_active))

    extra_keys = [k for k in status if k not in {"exchange_active", "trading_active"}]
    for key in sorted(extra_keys):
        table.add_row(key, str(status[key]))

    console.print(table)
