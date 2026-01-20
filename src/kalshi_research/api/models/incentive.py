"""Incentive program models for the Kalshi API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IncentiveProgram(BaseModel):
    """Incentive program as returned by `GET /incentive_programs`."""

    model_config = ConfigDict(frozen=True)

    id: str
    market_ticker: str
    incentive_type: str
    start_date: datetime
    end_date: datetime
    period_reward: int = Field(..., description="Reward amount in centi-cents.")
    paid_out: bool
    discount_factor_bps: int | None = None
    target_size: int | None = None


class IncentiveProgramsResponse(BaseModel):
    """Response schema for `GET /incentive_programs`."""

    model_config = ConfigDict(frozen=True)

    incentive_programs: list[IncentiveProgram]
    next_cursor: str | None = None

    @field_validator("next_cursor", mode="before")
    @classmethod
    def normalize_cursor(cls, value: object) -> str | None:
        """Normalize empty-string cursors to None (API may return \"\" for last page)."""
        if value is None or value == "":
            return None
        if isinstance(value, str):
            return value
        return str(value)
