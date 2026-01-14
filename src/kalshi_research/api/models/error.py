"""Error response models for Kalshi API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    """Error payload returned by the Kalshi API (OpenAPI ErrorResponse)."""

    model_config = ConfigDict(frozen=True)

    code: str | None = None
    message: str | None = None
    details: str | None = None
    service: str | None = None
