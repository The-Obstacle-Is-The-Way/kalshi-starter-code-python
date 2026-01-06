"""
Kalshi Research Platform.

A production-quality research platform for Kalshi prediction market analysis.
"""

__version__ = "0.1.0"

from kalshi_research.clients import (
    Environment,
    KalshiBaseClient,
    KalshiHttpClient,
    KalshiWebSocketClient,
)

__all__ = [
    "Environment",
    "KalshiBaseClient",
    "KalshiHttpClient",
    "KalshiWebSocketClient",
    "__version__",
]
