"""Answer endpoint methods for Exa API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kalshi_research.exa.models import AnswerRequest, AnswerResponse

if TYPE_CHECKING:
    import httpx

    from kalshi_research.exa.config import ExaConfig


class AnswerMixin:
    """Mixin providing answer-related Exa API methods."""

    _config: ExaConfig
    _client: httpx.AsyncClient | None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def answer(self, query: str, *, text: bool = False) -> AnswerResponse:
        """Generate an answer for a query via Exa `/answer`.

        Args:
            query: Question to answer.
            text: Whether to request full text for citations.

        Returns:
            Parsed `AnswerResponse`.

        Raises:
            ExaAuthError: If the API key is invalid.
            ExaRateLimitError: If rate-limited and retries are exhausted.
            ExaAPIError: For other API/network/response errors.
        """
        request = AnswerRequest(query=query, text=text)
        data = await self._request(
            "POST",
            "/answer",
            json_body=request.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return AnswerResponse.model_validate(data)
