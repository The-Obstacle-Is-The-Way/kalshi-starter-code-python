"""Async Exa API client.

This module provides the main `ExaClient` class, composed from focused mixins:
- `ExaHTTPBase`: HTTP request infrastructure and lifecycle management
- `ContentNormalizationMixin`: Content option normalization helpers
- `SearchMixin`: Search and find-similar endpoints
- `ContentsMixin`: Get-contents endpoint
- `AnswerMixin`: Answer endpoint
- `ResearchMixin`: Research task endpoints (create, get, list, wait)
"""

from __future__ import annotations

from kalshi_research.exa._answer import AnswerMixin
from kalshi_research.exa._contents import ContentsMixin
from kalshi_research.exa._http import ExaHTTPBase
from kalshi_research.exa._normalization import ContentNormalizationMixin
from kalshi_research.exa._research import ResearchMixin
from kalshi_research.exa._search import SearchMixin
from kalshi_research.exa.config import ExaConfig


class ExaClient(
    ExaHTTPBase,
    ContentNormalizationMixin,
    SearchMixin,
    ContentsMixin,
    AnswerMixin,
    ResearchMixin,
):
    """
    Async client for Exa API.

    Use as an async context manager:

        async with ExaClient.from_env() as exa:
            results = await exa.search("prediction markets")
    """

    def __init__(self, config: ExaConfig) -> None:
        super().__init__(config)

    @classmethod
    def from_env(cls) -> ExaClient:
        """Create an `ExaClient` using environment configuration.

        Raises:
            ValueError: If required environment variables (e.g., `EXA_API_KEY`) are missing.
        """
        return cls(ExaConfig.from_env())

    async def __aenter__(self) -> ExaClient:
        await self.open()
        return self
