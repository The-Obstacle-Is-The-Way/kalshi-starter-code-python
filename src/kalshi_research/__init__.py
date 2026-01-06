"""
Kalshi Research Platform.

A production-quality research platform for Kalshi prediction market analysis.
"""

__version__ = "0.1.0"

# Legacy sync clients (from original starter code)
from kalshi_research.clients import (
    Environment,
    KalshiBaseClient,
    KalshiHttpClient,
    KalshiWebSocketClient,
)

# New async API clients
from kalshi_research.api import KalshiClient, KalshiPublicClient

__all__ = [
    # Version
    "__version__",
    # New async clients (preferred)
    "KalshiClient",
    "KalshiPublicClient",
    # Legacy sync clients
    "Environment",
    "KalshiBaseClient",
    "KalshiHttpClient",
    "KalshiWebSocketClient",
]
