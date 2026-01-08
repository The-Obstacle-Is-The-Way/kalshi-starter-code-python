"""Custom exceptions for Kalshi API errors."""

from __future__ import annotations


class KalshiError(Exception):
    """Base exception for Kalshi API errors."""


class KalshiAPIError(KalshiError):
    """HTTP API error with status code."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")


class RateLimitError(KalshiAPIError):
    """Rate limit exceeded (HTTP 429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
    ) -> None:
        super().__init__(429, message)
        self.retry_after = retry_after


class AuthenticationError(KalshiAPIError):
    """Authentication failed (HTTP 401)."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(401, message)


class MarketNotFoundError(KalshiAPIError):
    """Market ticker not found (HTTP 404)."""

    def __init__(self, ticker: str) -> None:
        super().__init__(404, f"Market not found: {ticker}")
