"""Exa API errors and exception types."""

from __future__ import annotations


class ExaError(Exception):
    """Base exception for Exa API errors."""


class ExaAPIError(ExaError):
    """Generic API error."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code


class ExaAuthError(ExaAPIError):
    """Authentication error (invalid API key)."""


class ExaRateLimitError(ExaAPIError):
    """Rate limit exceeded."""

    def __init__(self, message: str, *, retry_after_seconds: int | None = None) -> None:
        super().__init__(message, status_code=429)
        self.retry_after_seconds = retry_after_seconds
