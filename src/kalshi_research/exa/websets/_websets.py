"""Webset CRUD operations for Exa Websets API."""

from __future__ import annotations

from typing import Any

from kalshi_research.exa.websets.models import (
    CreateWebsetParameters,
    GetWebsetResponse,
    PreviewWebsetParameters,
    PreviewWebsetResponse,
    Webset,
)


class ExaWebsetsMixin:
    """
    Webset CRUD operations.

    Provides:
    - create_webset: Create a new Webset
    - preview_webset: Preview a Webset search
    - get_webset: Get a Webset by ID
    - cancel_webset: Cancel a Webset

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

    async def create_webset(
        self,
        params: CreateWebsetParameters,
    ) -> Webset:
        """Create a new Webset via POST /v0/websets.

        Args:
            params: Parameters for creating the Webset.

        Returns:
            Created `Webset`.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaRateLimitError: If rate-limited and retries are exhausted.
            ExaAPIError: For other API/network/response errors.
        """
        data = await self._request(
            "POST",
            "/v0/websets",
            json_body=params.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return Webset.model_validate(data)

    async def preview_webset(
        self,
        params: PreviewWebsetParameters,
    ) -> PreviewWebsetResponse:
        """Preview a Webset search via POST /v0/websets/preview.

        Args:
            params: Parameters for previewing the Webset.

        Returns:
            Preview response with sample items.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaRateLimitError: If rate-limited and retries are exhausted.
            ExaAPIError: For other API/network/response errors.
        """
        data = await self._request(
            "POST",
            "/v0/websets/preview",
            json_body=params.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return PreviewWebsetResponse.model_validate(data)

    async def get_webset(self, webset_id: str) -> GetWebsetResponse:
        """Get a Webset by ID via GET /v0/websets/{id}.

        Args:
            webset_id: Webset ID.

        Returns:
            Webset details.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaAPIError: If the Webset is not found or other errors occur.
        """
        data = await self._request("GET", f"/v0/websets/{webset_id}")
        return GetWebsetResponse.model_validate(data)

    async def cancel_webset(self, webset_id: str) -> Webset:
        """Cancel a Webset via POST /v0/websets/{id}/cancel.

        Args:
            webset_id: Webset ID.

        Returns:
            Updated Webset with canceled status.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaAPIError: If the Webset is not found or other errors occur.
        """
        data = await self._request("POST", f"/v0/websets/{webset_id}/cancel")
        return Webset.model_validate(data)
