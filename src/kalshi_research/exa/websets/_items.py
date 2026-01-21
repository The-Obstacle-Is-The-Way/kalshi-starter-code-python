"""Webset item operations for Exa Websets API."""

from __future__ import annotations

from typing import Any

from kalshi_research.exa.websets.models import (
    ListWebsetItemResponse,
    WebsetItem,
)


class ExaWebsetsItemsMixin:
    """
    Webset item operations.

    Provides:
    - list_webset_items: List items in a Webset
    - get_webset_item: Get a specific item from a Webset

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

    async def list_webset_items(
        self,
        webset_id: str,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> ListWebsetItemResponse:
        """List items in a Webset via GET /v0/websets/{webset}/items.

        Args:
            webset_id: Webset ID.
            cursor: Optional pagination cursor.
            limit: Page size (default 20).

        Returns:
            List of Webset items.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaAPIError: If the Webset is not found or other errors occur.
        """
        params: dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        data = await self._request("GET", f"/v0/websets/{webset_id}/items", params=params)
        return ListWebsetItemResponse.model_validate(data)

    async def get_webset_item(
        self,
        webset_id: str,
        item_id: str,
    ) -> WebsetItem:
        """Get a specific item from a Webset via GET /v0/websets/{webset}/items/{id}.

        Args:
            webset_id: Webset ID.
            item_id: Item ID.

        Returns:
            Webset item details.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaAPIError: If the item is not found or other errors occur.
        """
        data = await self._request("GET", f"/v0/websets/{webset_id}/items/{item_id}")
        return WebsetItem.model_validate(data)
