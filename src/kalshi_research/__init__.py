"""
Kalshi Research Platform.

A production-quality research platform for Kalshi prediction market analysis.
"""

__version__ = "0.1.0"

# Legacy sync clients (from original starter code)
# New async API clients
from kalshi_research.api import KalshiClient, KalshiPublicClient
from kalshi_research.clients import (
    Environment,
    KalshiBaseClient,
    KalshiHttpClient,
    KalshiWebSocketClient,
)

__all__ = [
    "Environment",
    "KalshiBaseClient",
    "KalshiClient",
    "KalshiHttpClient",
    "KalshiPublicClient",
    "KalshiWebSocketClient",
    "__version__",
]
