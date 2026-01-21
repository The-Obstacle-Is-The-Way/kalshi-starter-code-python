"""Webset search operations for Exa Websets API."""

from __future__ import annotations

from typing import Any

from kalshi_research.exa.websets.models import (
    CreateWebsetSearchParameters,
    WebsetSearch,
)


class ExaWebsetsSearchesMixin:
    """
    Webset search operations.

    Provides:
    - create_webset_search: Create a new search in a Webset
    - get_webset_search: Get a search from a Webset
    - cancel_webset_search: Cancel a search in a Webset

    Note: This mixin expects `_request` to be provided by the composing class.
    """

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def create_webset_search(
        self,
        webset_id: str,
        params: CreateWebsetSearchParameters,
    ) -> WebsetSearch:
        """Create a new search in a Webset via POST /v0/websets/{webset}/searches.

        Args:
            webset_id: Webset ID.
            params: Search parameters.

        Returns:
            Created search.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaAPIError: If the Webset is not found or other errors occur.
        """
        data = await self._request(
            "POST",
            f"/v0/websets/{webset_id}/searches",
            json_body=params.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return WebsetSearch.model_validate(data)

    async def get_webset_search(
        self,
        webset_id: str,
        search_id: str,
    ) -> WebsetSearch:
        """Get a search from a Webset via GET /v0/websets/{webset}/searches/{id}.

        Args:
            webset_id: Webset ID.
            search_id: Search ID.

        Returns:
            Search details.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaAPIError: If the search is not found or other errors occur.
        """
        data = await self._request("GET", f"/v0/websets/{webset_id}/searches/{search_id}")
        return WebsetSearch.model_validate(data)

    async def cancel_webset_search(
        self,
        webset_id: str,
        search_id: str,
    ) -> WebsetSearch:
        """Cancel a search in a Webset via POST /v0/websets/{webset}/searches/{id}/cancel.

        Args:
            webset_id: Webset ID.
            search_id: Search ID.

        Returns:
            Updated search with canceled status.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaAPIError: If the search is not found or other errors occur.
        """
        data = await self._request("POST", f"/v0/websets/{webset_id}/searches/{search_id}/cancel")
        return WebsetSearch.model_validate(data)
