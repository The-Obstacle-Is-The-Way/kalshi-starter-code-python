"""Event data models for Kalshi API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Event(BaseModel):
    """Event as returned by the Kalshi API."""

    model_config = ConfigDict(frozen=True)

    event_ticker: str = Field(..., description="Unique event identifier")
    series_ticker: str = Field(..., description="Parent series ticker")
    title: str
    sub_title: str = ""
    category: str | None = None

    mutually_exclusive: bool = False
    available_on_brokers: bool = False

    collateral_return_type: str = ""
    strike_period: str = ""
    strike_date: datetime | None = None

    @field_validator("strike_date", mode="before")
    @classmethod
    def _empty_str_to_none(cls, value: Any) -> Any:
        if value in ("", None):
            return None
        return value
