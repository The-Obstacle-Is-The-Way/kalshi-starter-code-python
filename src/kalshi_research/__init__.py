"""
Kalshi Research Platform.

Internal single-user research tooling for Kalshi prediction market analysis.
"""

__version__ = "0.1.0"

# Modern async API clients
from kalshi_research.api import KalshiClient, KalshiPublicClient
from kalshi_research.api.config import Environment

__all__ = [
    "Environment",
    "KalshiClient",
    "KalshiPublicClient",
    "__version__",
]
