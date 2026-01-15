"""Search and discovery models for the Kalshi API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TagsByCategoriesResponse(BaseModel):
    """Response schema for `GET /search/tags_by_categories`."""

    model_config = ConfigDict(frozen=True)

    tags_by_categories: dict[str, list[str] | None] = Field(
        ...,
        description="Mapping of series categories to their associated tags.",
    )


class ScopeList(BaseModel):
    """Scope list container as returned in sports filter responses."""

    model_config = ConfigDict(frozen=True)

    scopes: list[str]


class SportFilterDetails(BaseModel):
    """Filter details for a single sport in `GET /search/filters_by_sport`."""

    model_config = ConfigDict(frozen=True)

    scopes: list[str]
    competitions: dict[str, ScopeList]


class FiltersBySportsResponse(BaseModel):
    """Response schema for `GET /search/filters_by_sport`."""

    model_config = ConfigDict(frozen=True)

    filters_by_sports: dict[str, SportFilterDetails]
    sport_ordering: list[str]
