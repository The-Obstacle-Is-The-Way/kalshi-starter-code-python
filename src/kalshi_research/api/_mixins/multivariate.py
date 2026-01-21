"""Multivariate event collections endpoint mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kalshi_research.api.models.multivariate import (
    GetMultivariateEventCollectionResponse,
    GetMultivariateEventCollectionsResponse,
    MultivariateEventCollection,
)


class MultivariateMixin:
    """Mixin providing multivariate event collection endpoints (public)."""

    if TYPE_CHECKING:
        # Implemented by ClientBase
        async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]: ...

    async def get_multivariate_event_collections(
        self,
        *,
        status: str | None = None,
        associated_event_ticker: str | None = None,
        series_ticker: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> GetMultivariateEventCollectionsResponse:
        """
        List multivariate event collections with optional filters.

        Args:
            status: Optional filter (`unopened`, `open`, `closed`).
            associated_event_ticker: Optional associated event filter.
            series_ticker: Optional series filter.
            limit: Page size (1-200).
            cursor: Pagination cursor from a prior response.
        """
        params: dict[str, Any] = {"limit": max(1, min(limit, 200))}
        if status is not None:
            params["status"] = status
        if associated_event_ticker is not None:
            params["associated_event_ticker"] = associated_event_ticker
        if series_ticker is not None:
            params["series_ticker"] = series_ticker
        if cursor is not None:
            params["cursor"] = cursor

        data = await self._get("/multivariate_event_collections", params)
        return GetMultivariateEventCollectionsResponse.model_validate(data)

    async def get_multivariate_event_collection(
        self, collection_ticker: str
    ) -> MultivariateEventCollection:
        """Fetch a single multivariate event collection by ticker."""
        data = await self._get(f"/multivariate_event_collections/{collection_ticker}")
        parsed = GetMultivariateEventCollectionResponse.model_validate(data)
        return parsed.multivariate_contract
