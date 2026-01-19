"""
CLI application for Kalshi Research Platform.

Provides commands for data collection, analysis, and research.
"""

from __future__ import annotations

import os
from typing import Annotated

import typer
from dotenv import find_dotenv, load_dotenv

from kalshi_research.cli.agent import app as agent_app
from kalshi_research.cli.alerts import app as alerts_app
from kalshi_research.cli.analysis import app as analysis_app
from kalshi_research.cli.browse import app as browse_app
from kalshi_research.cli.data import app as data_app
from kalshi_research.cli.event import app as event_app
from kalshi_research.cli.market import app as market_app
from kalshi_research.cli.mve import app as mve_app
from kalshi_research.cli.news import app as news_app
from kalshi_research.cli.portfolio import app as portfolio_app
from kalshi_research.cli.research import app as research_app
from kalshi_research.cli.scan import app as scan_app
from kalshi_research.cli.series import app as series_app
from kalshi_research.cli.status import app as status_app
from kalshi_research.cli.utils import console
from kalshi_research.logging import configure_structlog

app = typer.Typer(
    name="kalshi",
    help="Kalshi Research Platform CLI - Tools for prediction market research.",
    add_completion=False,
)

app.add_typer(agent_app, name="agent")
app.add_typer(data_app, name="data")
app.add_typer(market_app, name="market")
app.add_typer(scan_app, name="scan")
app.add_typer(browse_app, name="browse")
app.add_typer(series_app, name="series")
app.add_typer(event_app, name="event")
app.add_typer(mve_app, name="mve")
app.add_typer(status_app, name="status")
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
    from kalshi_research.api.config import Environment, set_environment

    load_dotenv(find_dotenv(usecwd=True))
    configure_structlog()

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
