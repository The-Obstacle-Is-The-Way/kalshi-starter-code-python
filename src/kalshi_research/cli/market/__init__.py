"""Typer CLI commands for market lookup and exploration.

This package provides market commands for the Kalshi CLI:
- get: Fetch a single market by ticker
- orderbook: Fetch orderbook for a market
- liquidity: Analyze market liquidity
- history: Fetch candlestick history for a market
- list: List markets with optional filters
- search: Search markets in the local database
"""

import typer

from kalshi_research.cli.market._helpers import (
    normalize_market_list_status,
    optional_lower,
)
from kalshi_research.cli.market.get import market_get
from kalshi_research.cli.market.history import market_history
from kalshi_research.cli.market.liquidity import market_liquidity
from kalshi_research.cli.market.list import (
    fetch_markets_from_events,
    filter_markets_by_event_ticker,
    market_list,
    market_list_async,
    render_market_list_table,
)
from kalshi_research.cli.market.orderbook import market_orderbook
from kalshi_research.cli.market.search import market_search

# Create main app and register commands
app = typer.Typer(help="Market lookup commands.")

app.command("get")(market_get)
app.command("orderbook")(market_orderbook)
app.command("liquidity")(market_liquidity)
app.command("history")(market_history)
app.command("list")(market_list)
app.command("search")(market_search)

# Public API exports for backwards compatibility
__all__ = [
    "app",
    "fetch_markets_from_events",
    "filter_markets_by_event_ticker",
    "market_get",
    "market_history",
    "market_liquidity",
    "market_list",
    "market_list_async",
    "market_orderbook",
    "market_search",
    "normalize_market_list_status",
    "optional_lower",
    "render_market_list_table",
]
