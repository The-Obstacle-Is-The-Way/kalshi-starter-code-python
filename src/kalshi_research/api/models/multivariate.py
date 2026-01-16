"""Multivariate event collection models for the Kalshi API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MultivariateAssociatedEvent(BaseModel):
    """Associated event constraints inside a multivariate event collection."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    is_yes_only: bool
    size_max: int | None = None
    size_min: int | None = None
    active_quoters: list[str] = Field(default_factory=list)


class MultivariateEventCollection(BaseModel):
    """Multivariate event collection as returned by Kalshi's multivariate endpoints."""

    model_config = ConfigDict(frozen=True)

    collection_ticker: str
    series_ticker: str
    title: str
    description: str
    open_date: datetime
    close_date: datetime
    associated_events: list[MultivariateAssociatedEvent]
    associated_event_tickers: list[str]
    is_ordered: bool
    is_single_market_per_event: bool
    is_all_yes: bool
    size_min: int
    size_max: int
    functional_description: str


class GetMultivariateEventCollectionsResponse(BaseModel):
    """Response schema for `GET /multivariate_event_collections`."""

    model_config = ConfigDict(frozen=True)

    multivariate_contracts: list[MultivariateEventCollection]
    cursor: str | None = None


class GetMultivariateEventCollectionResponse(BaseModel):
    """Response schema for `GET /multivariate_event_collections/{collection_ticker}`."""

    model_config = ConfigDict(frozen=True)

    multivariate_contract: MultivariateEventCollection


class TickerPair(BaseModel):
    """Selected market input for multivariate lookup/create endpoints."""

    model_config = ConfigDict(frozen=True)

    market_ticker: str
    event_ticker: str
    side: Literal["yes", "no"]


class LookupTickersForMarketInMultivariateEventCollectionRequest(BaseModel):
    """Request schema for `PUT /multivariate_event_collections/{collection_ticker}/lookup`."""

    model_config = ConfigDict(frozen=True)

    selected_markets: list[TickerPair]


class LookupTickersForMarketInMultivariateEventCollectionResponse(BaseModel):
    """Response schema for `PUT /multivariate_event_collections/{collection_ticker}/lookup`."""

    model_config = ConfigDict(frozen=True)

    event_ticker: str
    market_ticker: str
