"""Async Exa Websets API client."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kalshi_research.exa.config import ExaConfig

if TYPE_CHECKING:
    import httpx
from kalshi_research.exa.websets._http import ExaWebsetsHttpMixin
from kalshi_research.exa.websets._items import ExaWebsetsItemsMixin
from kalshi_research.exa.websets._searches import ExaWebsetsSearchesMixin
from kalshi_research.exa.websets._websets import ExaWebsetsMixin


class ExaWebsetsClient(
    ExaWebsetsHttpMixin,
    ExaWebsetsMixin,
    ExaWebsetsItemsMixin,
    ExaWebsetsSearchesMixin,
):
    """
    Async client for Exa Websets API.

    Use as an async context manager:

        async with ExaWebsetsClient.from_env() as client:
            webset = await client.create_webset(
                CreateWebsetParameters(
                    search=CreateWebsetSearchParameters(
                        query="AI startups in Europe",
                        count=10
                    )
                )
            )
    """

    def __init__(self, config: ExaConfig) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None

    @classmethod
    def from_env(cls) -> ExaWebsetsClient:
        """Create an `ExaWebsetsClient` using environment configuration.

        Raises:
            ValueError: If required environment variables (e.g., `EXA_API_KEY`) are missing.
        """
        return cls(ExaConfig.from_env())

    async def __aenter__(self) -> ExaWebsetsClient:
        await self.open()
        return self
