"""Typer CLI commands for scanning markets and surfacing opportunities.

This package provides market scanning commands for the Kalshi CLI:
- opportunities: Scan markets for opportunities (close races, high volume, etc.)
- new-markets: Show markets created in the last N hours
- arbitrage: Find arbitrage opportunities from correlated markets
- movers: Show biggest price movers over a time period
"""

import typer

from kalshi_research.cli.scan._helpers import NewMarketRow
from kalshi_research.cli.scan._opportunities_helpers import ScanProfile

# Re-export symbols for backwards compatibility with tests that import from cli.scan
from kalshi_research.cli.scan.arbitrage import (
    _format_opportunity_tickers,
    _load_correlated_pairs,
    _render_arbitrage_opportunities_table,
    _scan_arbitrage_async,
    scan_arbitrage,
)
from kalshi_research.cli.scan.movers import (
    MoverRow,
    _compute_movers,
    _fetch_movers_market_lookup,
    _parse_movers_period,
    _render_movers_table,
    _scan_movers_async,
    scan_movers,
)
from kalshi_research.cli.scan.new_markets import (
    _build_new_markets_results,
    _collect_new_market_candidates,
    _format_relative_age,
    _get_event_category,
    _is_unpriced_market,
    _iter_open_markets,
    _market_yes_price_display,
    _parse_category_filter,
    _render_new_markets_table,
    _scan_new_markets_async,
    _validate_new_markets_args,
    scan_new_markets,
)
from kalshi_research.cli.scan.opportunities import (
    _compute_liquidity_scores,
    _fetch_exchange_status,
    _fetch_opportunities_markets,
    _filter_markets_by_age,
    _filter_results_by_liquidity,
    _render_opportunities_table,
    _scan_opportunities_async,
    _scan_profile_defaults,
    _select_opportunity_results,
    scan_opportunities,
)

# Create main app
app = typer.Typer(help="Market scanning commands.")

# Register commands
app.command("opportunities")(scan_opportunities)
app.command("new-markets")(scan_new_markets)
app.command("arbitrage")(scan_arbitrage)
app.command("movers")(scan_movers)

# Public API exports
__all__ = [
    # Type aliases
    "MoverRow",
    "NewMarketRow",
    "ScanProfile",
    # New markets
    "_build_new_markets_results",
    "_collect_new_market_candidates",
    # Opportunities
    "_compute_liquidity_scores",
    # Movers
    "_compute_movers",
    "_fetch_exchange_status",
    "_fetch_movers_market_lookup",
    "_fetch_opportunities_markets",
    "_filter_markets_by_age",
    "_filter_results_by_liquidity",
    # Arbitrage
    "_format_opportunity_tickers",
    "_format_relative_age",
    "_get_event_category",
    "_is_unpriced_market",
    "_iter_open_markets",
    "_load_correlated_pairs",
    "_market_yes_price_display",
    "_parse_category_filter",
    "_parse_movers_period",
    "_render_arbitrage_opportunities_table",
    "_render_movers_table",
    "_render_new_markets_table",
    "_render_opportunities_table",
    "_scan_arbitrage_async",
    "_scan_movers_async",
    "_scan_new_markets_async",
    "_scan_opportunities_async",
    "_scan_profile_defaults",
    "_select_opportunity_results",
    "_validate_new_markets_args",
    # Main app
    "app",
    # Commands (for direct registration if needed)
    "scan_arbitrage",
    "scan_movers",
    "scan_new_markets",
    "scan_opportunities",
]
