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


@app.callback()
def main(
    environment: Annotated[
        str,
        typer.Option(
            "--env",
            "-e",
            help="API environment (prod/demo). Defaults to KALSHI_ENVIRONMENT or prod.",
        ),
    ] = "prod",
) -> None:
    """Kalshi Research Platform CLI."""
    import os

    from kalshi_research.api.config import Environment, set_environment

    load_dotenv(find_dotenv(usecwd=True))

    # Priority: CLI flag > KALSHI_ENVIRONMENT env var > default "prod"
    env_var = os.getenv("KALSHI_ENVIRONMENT")

    # If user didn't override --env (still "prod") and env var is set, use env var
    final_env = environment
    if environment == "prod" and env_var:
        final_env = env_var

    try:
        set_environment(Environment(final_env))
    except ValueError:
        console.print(
            f"[yellow]Warning:[/yellow] Invalid environment '{final_env}', defaulting to prod"
        )
        set_environment(Environment.PRODUCTION)


@app.command()
def version() -> None:
    """Show version information."""
    from kalshi_research import __version__

    console.print(f"kalshi-research v{__version__}")
