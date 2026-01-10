"""
Jupyter notebook utilities for Kalshi research.

Usage:
    from kalshi_research.research.notebook_utils import setup_notebook, load_markets

    setup_notebook()  # Configure display settings
    markets = await load_markets()  # Load market data
"""

from __future__ import annotations

import asyncio
from typing import Any

import pandas as pd
import structlog

from kalshi_research.analysis.edge import Edge
from kalshi_research.api import KalshiPublicClient
from kalshi_research.api.models import Market

# Optional imports for Jupyter/IPython
try:
    from IPython import get_ipython
    from IPython.display import HTML, display

    IPYTHON_AVAILABLE = True
except ImportError:
    IPYTHON_AVAILABLE = False

logger = structlog.get_logger()

try:
    plt: Any | None
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    plt = None
    MATPLOTLIB_AVAILABLE = False


def setup_notebook(
    pd_max_rows: int = 100,
    pd_max_cols: int = 20,
    figure_format: str = "retina",
) -> None:
    """
    Configure notebook display settings.

    Args:
        pd_max_rows: Max pandas rows to display
        pd_max_cols: Max pandas columns to display
        figure_format: Matplotlib figure format (retina for HiDPI)
    """
    # Pandas display options
    pd.set_option("display.max_rows", pd_max_rows)
    pd.set_option("display.max_columns", pd_max_cols)
    pd.set_option("display.width", 1000)
    pd.set_option("display.float_format", "{:.4f}".format)

    # Matplotlib settings
    if MATPLOTLIB_AVAILABLE and IPYTHON_AVAILABLE and plt is not None:
        try:
            ipython = get_ipython()
            if ipython:
                ipython.run_line_magic("matplotlib", "inline")
                ipython.run_line_magic("config", f"InlineBackend.figure_format = '{figure_format}'")

            plt.style.use("seaborn-v0_8-whitegrid")
            plt.rcParams["figure.figsize"] = (12, 6)
            plt.rcParams["font.size"] = 12
        except Exception as e:
            logger.warning("setup_notebook() matplotlib configuration failed", error=str(e))

    print("Notebook configured for Kalshi research.")


async def load_markets(
    status: str = "open",
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Load markets into a pandas DataFrame.

    Args:
        status: Market status filter (open, closed, settled)
        limit: Max markets to load

    Returns:
        DataFrame with market data
    """
    async with KalshiPublicClient() as client:
        markets: list[dict[str, Any]] = []
        count = 0

        async for market in client.get_all_markets(status=status):
            if limit is not None and count >= limit:
                break
            markets.append(
                {
                    "ticker": market.ticker,
                    "title": market.title,
                    "subtitle": market.subtitle,
                    "yes_price": market.midpoint / 100.0,
                    "yes_bid": market.yes_bid_cents,
                    "yes_ask": market.yes_ask_cents,
                    "spread": market.spread,
                    "volume": market.volume,
                    "open_interest": market.open_interest,
                    "close_time": market.close_time,
                    "status": market.status,
                    "event_ticker": market.event_ticker,
                }
            )

            count += 1

    return pd.DataFrame(markets)


async def load_events(limit: int | None = None) -> pd.DataFrame:
    """Load events into a DataFrame."""
    async with KalshiPublicClient() as client:
        events: list[dict[str, Any]] = []
        count = 0

        async for event in client.get_all_events():
            if limit is not None and count >= limit:
                break
            events.append(
                {
                    "event_ticker": event.event_ticker,
                    "title": event.title,
                    "category": event.category,
                    "mutually_exclusive": event.mutually_exclusive,
                }
            )

            count += 1

    return pd.DataFrame(events)


def display_market(market: Market) -> None:
    """
    Rich display of a single market in Jupyter.

    Args:
        market: Market to display
    """
    if not IPYTHON_AVAILABLE:
        print(f"Market: {market.ticker}")
        return

    html = f"""
    <div style="border: 1px solid #ddd; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <h3 style="margin-top: 0;">{market.ticker}</h3>
        <p><strong>{market.title}</strong></p>
        <p><em>{market.subtitle}</em></p>
        <table style="width: 100%;">
            <tr>
                <td><strong>YES Price:</strong></td>
                <td>{market.midpoint:.1f}c ({market.midpoint / 100:.0%})</td>
                <td><strong>Volume:</strong></td>
                <td>{market.volume:,}</td>
            </tr>
            <tr>
                <td><strong>Bid/Ask:</strong></td>
                <td>{market.yes_bid_cents}c / {market.yes_ask_cents}c (spread: {market.spread}c)</td>
                <td><strong>Open Interest:</strong></td>
                <td>{market.open_interest:,}</td>
            </tr>
            <tr>
                <td><strong>Status:</strong></td>
                <td>{market.status}</td>
                <td><strong>Closes:</strong></td>
                <td>{market.close_time.strftime("%Y-%m-%d %H:%M UTC") if market.close_time else "N/A"}</td>
            </tr>
        </table>
    </div>
    """
    display(HTML(html))


def display_edge(edge: Edge) -> None:
    """
    Rich display of a detected edge in Jupyter.

    Args:
        edge: Edge to display
    """
    if not IPYTHON_AVAILABLE:
        print(f"Edge: {edge.ticker}")
        return

    yours = f"{edge.your_estimate:.0%}" if edge.your_estimate else "N/A"
    ev = f"{edge.expected_value:+.1f}c" if edge.expected_value else "N/A"

    color = "green" if (edge.expected_value or 0) > 0 else "red"

    html = f"""
    <div style="border: 2px solid {color}; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <h4 style="margin-top: 0; color: {color};">[{edge.edge_type.value.upper()}] {edge.ticker}</h4>
        <table style="width: 100%;">
            <tr>
                <td><strong>Market Price:</strong></td>
                <td>{edge.market_price:.0%}</td>
                <td><strong>Your Estimate:</strong></td>
                <td>{yours}</td>
            </tr>
            <tr>
                <td><strong>Expected Value:</strong></td>
                <td style="color: {color}; font-weight: bold;">{ev}</td>
                <td><strong>Confidence:</strong></td>
                <td>{edge.confidence:.0%}</td>
            </tr>
        </table>
        <p style="margin-bottom: 0;"><em>{edge.description}</em></p>
    </div>
    """
    display(HTML(html))


def display_markets_table(
    markets: list[Market] | pd.DataFrame,
    columns: list[str] | None = None,
) -> None:
    """
    Display markets in a table format.

    Args:
        markets: List of markets or DataFrame
        columns: Columns to include (defaults to key columns)
    """
    if not IPYTHON_AVAILABLE:
        print(f"Markets: {len(markets)}")
        return

    if columns is None:
        columns = ["ticker", "title", "yes_price", "spread", "volume", "status"]

    if isinstance(markets, pd.DataFrame):
        df = markets
    else:
        df = pd.DataFrame(
            [
                {
                    "ticker": m.ticker,
                    "title": m.title[:50] + "..." if len(m.title) > 50 else m.title,
                    "yes_price": f"{m.midpoint:.1f}c",
                    "spread": f"{m.spread}c",
                    "volume": f"{m.volume:,}",
                    "status": m.status,
                }
                for m in markets
            ]
        )

    display(df[columns].head(20))


# Helper for running async in notebooks
def run_async(coro: Any) -> Any:
    """
    Run async coroutine in notebook.

    Usage:
        markets = run_async(load_markets())
    """
    try:
        # Check if there's already a running event loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop - safe to use asyncio.run()
        return asyncio.run(coro)

    # Already in async context (e.g., Jupyter with async enabled)
    try:
        import nest_asyncio

        nest_asyncio.apply()
    except ImportError:
        raise RuntimeError(
            "run_async() cannot synchronously wait for a coroutine from a running event loop "
            "without nest_asyncio installed. Prefer `await coro` in async contexts."
        ) from None
    return loop.run_until_complete(coro)
