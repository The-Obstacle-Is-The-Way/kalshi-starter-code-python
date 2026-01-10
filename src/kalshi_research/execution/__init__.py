"""Trading execution safety harness (safe-by-default)."""

from kalshi_research.execution.executor import TradeExecutor, TradeSafetyError

__all__ = ["TradeExecutor", "TradeSafetyError"]
