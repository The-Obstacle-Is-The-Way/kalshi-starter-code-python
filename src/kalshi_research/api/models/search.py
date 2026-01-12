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
