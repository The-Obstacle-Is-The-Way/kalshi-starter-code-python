"""Typer CLI commands for portfolio tracking and P&L reporting.

This package provides portfolio commands for the Kalshi CLI:
- sync: Sync positions, trades, and settlements from Kalshi API
- positions: View current positions
- pnl: View profit and loss summary
- balance: View account balance
- history: View trade history
- link: Link a position to a thesis
- suggest-links: Suggest thesis-position links based on matching tickers
"""

import typer

from kalshi_research.cli.portfolio._helpers import (
    PORTFOLIO_SYNC_TIP,
    format_signed_currency,
    load_theses,
    require_auth_env,
    resolve_rate_tier_override,
    validate_environment_override,
)
from kalshi_research.cli.portfolio.balance import portfolio_balance
from kalshi_research.cli.portfolio.history import portfolio_history
from kalshi_research.cli.portfolio.link import portfolio_link, portfolio_suggest_links
from kalshi_research.cli.portfolio.pnl_cmd import portfolio_pnl
from kalshi_research.cli.portfolio.positions import portfolio_positions
from kalshi_research.cli.portfolio.sync import portfolio_sync

# Create main app and register commands
app = typer.Typer(help="Portfolio tracking and P&L commands.")

app.command("sync")(portfolio_sync)
app.command("positions")(portfolio_positions)
app.command("pnl")(portfolio_pnl)
app.command("balance")(portfolio_balance)
app.command("history")(portfolio_history)
app.command("link")(portfolio_link)
app.command("suggest-links")(portfolio_suggest_links)

# Public API exports for backwards compatibility
__all__ = [
    "PORTFOLIO_SYNC_TIP",
    "app",
    "format_signed_currency",
    "load_theses",
    "portfolio_balance",
    "portfolio_history",
    "portfolio_link",
    "portfolio_pnl",
    "portfolio_positions",
    "portfolio_suggest_links",
    "portfolio_sync",
    "require_auth_env",
    "resolve_rate_tier_override",
    "validate_environment_override",
]
