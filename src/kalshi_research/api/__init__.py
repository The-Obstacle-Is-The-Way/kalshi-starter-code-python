"""Kalshi API client module."""

from kalshi_research.api.auth import KalshiAuth
from kalshi_research.api.client import KalshiClient, KalshiPublicClient
from kalshi_research.api.exceptions import (
    AuthenticationError,
    KalshiAPIError,
    KalshiError,
    MarketNotFoundError,
    RateLimitError,
)
from kalshi_research.api.models import (
    CandlePrice,
    CandleSide,
    Candlestick,
    CandlestickResponse,
    Event,
    Market,
    MarketFilterStatus,
    MarketStatus,
    Orderbook,
    Trade,
)

__all__ = [
    # Clients
    "KalshiAuth",
    "KalshiClient",
    "KalshiPublicClient",
    # Exceptions
    "AuthenticationError",
    "KalshiAPIError",
    "KalshiError",
    "MarketNotFoundError",
    "RateLimitError",
    # Models
    "CandlePrice",
    "CandleSide",
    "Candlestick",
    "CandlestickResponse",
    "Event",
    "Market",
    "MarketFilterStatus",
    "MarketStatus",
    "Orderbook",
    "Trade",
]
