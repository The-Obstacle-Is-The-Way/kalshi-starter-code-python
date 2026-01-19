"""Series data models for Kalshi API."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FeeType(str, Enum):
    """Series fee structure type (OpenAPI `FeeType`)."""

    QUADRATIC = "quadratic"
    QUADRATIC_WITH_MAKER_FEES = "quadratic_with_maker_fees"
    FLAT = "flat"


class SettlementSource(BaseModel):
    """Settlement source entry (OpenAPI `SettlementSource`)."""

    model_config = ConfigDict(frozen=True)

    name: str | None = None
    url: str | None = None


class Series(BaseModel):
    """Series as returned by the Kalshi API (OpenAPI `Series`)."""

    model_config = ConfigDict(frozen=True)

    ticker: str = Field(..., description="Ticker that identifies this series.")
    frequency: str = Field(
        ...,
        description="Human-readable frequency description (e.g., weekly, daily, one-off).",
    )
    title: str = Field(
        ...,
        description="Series title. Combine with event title for full context.",
    )
    category: str = Field(..., description="Category which this series belongs to.")
    tags: list[str] = Field(
        default_factory=list,
        description="Tags describing subjects this series relates to.",
    )
    settlement_sources: list[SettlementSource] = Field(
        ...,
        description="Official sources used for market determination within the series.",
    )
    contract_url: str = Field(
        ...,
        description="Direct link to the original filing of the contract underlying the series.",
    )
    contract_terms_url: str = Field(
        ...,
        description="URL to the current terms of the contract underlying the series.",
    )
    product_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Internal product metadata of the series (may be absent).",
    )
    fee_type: FeeType = Field(..., description="Fee structure for this series.")
    fee_multiplier: float = Field(..., description="Multiplier applied to fee calculations.")
    additional_prohibitions: list[str] = Field(
        default_factory=list,
        description="Additional trading prohibitions for this series.",
    )
    volume: int | None = Field(
        default=None,
        description="Total contracts traded across all events (only when include_volume=true).",
    )

    @field_validator("tags", "additional_prohibitions", mode="before")
    @classmethod
    def _none_to_empty_list(cls, value: Any) -> Any:
        # SSOT: API returns `null` for empty arrays on some series objects.
        if value is None:
            return []
        return value


class SeriesResponse(BaseModel):
    """Response schema for `GET /series/{series_ticker}`."""

    model_config = ConfigDict(frozen=True)

    series: Series


class SeriesListResponse(BaseModel):
    """Response schema for `GET /series`."""

    model_config = ConfigDict(frozen=True)

    series: list[Series]
