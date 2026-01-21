"""Trading execution safety harness (safe-by-default)."""

from kalshi_research.execution._executor import TradeExecutor, TradeSafetyError
from kalshi_research.execution._protocols import (
    DailyBudgetTracker,
    MarketProvider,
    OrderbookProvider,
    PositionProvider,
)

__all__ = [
    "DailyBudgetTracker",
    "MarketProvider",
    "OrderbookProvider",
    "PositionProvider",
    "TradeExecutor",
    "TradeSafetyError",
]
