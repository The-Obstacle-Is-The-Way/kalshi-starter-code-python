"""Series and search endpoint mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kalshi_research.api.models.search import FiltersBySportsResponse, TagsByCategoriesResponse
from kalshi_research.api.models.series import (
    Series,
    SeriesListResponse,
    SeriesResponse,
)


class SeriesMixin:
    """Mixin providing series and search-related endpoints."""

    if TYPE_CHECKING:
        # Implemented by ClientBase
        async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]: ...

    async def get_tags_by_categories(self) -> dict[str, list[str]]:
        """Fetch category->tags mapping for series discovery."""
        data = await self._get("/search/tags_by_categories")
        parsed = TagsByCategoriesResponse.model_validate(data)
        return {
            category: (tags if tags is not None else [])
            for category, tags in parsed.tags_by_categories.items()
        }

    async def get_filters_by_sport(self) -> FiltersBySportsResponse:
        """Fetch sport-specific filters for discovery UIs."""
        data = await self._get("/search/filters_by_sport")
        return FiltersBySportsResponse.model_validate(data)

    async def get_series_list(
        self,
        *,
        category: str | None = None,
        tags: str | None = None,
        include_product_metadata: bool = False,
        include_volume: bool = False,
    ) -> list[Series]:
        """
        List available series with optional filters.

        This is the intended Kalshi browse pattern:
        `/search/tags_by_categories` -> `/series` -> `/markets?series_ticker=...`.
        """
        params: dict[str, Any] = {}
        if category is not None:
            params["category"] = category
        if tags is not None:
            params["tags"] = tags
        if include_product_metadata:
            params["include_product_metadata"] = True
        if include_volume:
            params["include_volume"] = True

        data = await self._get("/series", params or None)
        return SeriesListResponse.model_validate(data).series

    async def get_series(
        self,
        series_ticker: str,
        *,
        include_volume: bool = False,
    ) -> Series:
        """Fetch a single series by ticker."""
        params: dict[str, Any] = {}
        if include_volume:
            params["include_volume"] = True
        data = await self._get(f"/series/{series_ticker}", params or None)
        return SeriesResponse.model_validate(data).series
