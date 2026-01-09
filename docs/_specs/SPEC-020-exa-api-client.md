# SPEC-020: Exa API Client Foundation

**Status:** 📋 Planned
**Priority:** P1 (Enables all Exa integrations)
**Estimated Complexity:** Medium
**Dependencies:** SPEC-001, SPEC-002

---

## 1. Overview

Build a properly typed, async Exa API client that follows the same patterns as our Kalshi client. This client becomes the foundation for all Exa-powered research features.

### 1.1 Goals

- Async-first client using httpx (consistent with KalshiPublicClient)
- Full type safety with Pydantic v2 models for all responses
- Rate limiting and retry logic
- Support for Search, Contents, Find Similar, Answer, and Research endpoints
- Optional caching layer for expensive operations
- Test infrastructure with respx mocks (minimal mocking philosophy)

### 1.2 Non-Goals

- Complex orchestration (that's SPEC-024)
- Database persistence of Exa results (that's SPEC-022)
- Thesis integration (that's SPEC-023)
- UI/CLI commands (deferred to feature specs)
- MCP server integration (use native Exa MCP for interactive Claude sessions)

### 1.3 MCP vs SDK Decision

Exa provides an [official MCP server](https://github.com/exa-labs/exa-mcp-server) for native Claude integration. Here's when to use each:

| Use Case | Recommendation |
|----------|----------------|
| **This SDK** | Production pipelines, typed code, testable, programmatic access |
| **MCP Server** | Interactive Claude sessions, quick prototyping, notebook exploration |

**This spec focuses on the SDK approach** because:
1. We need type-safe, testable code for production features
2. respx mocking requires direct httpx control
3. CLI commands need programmatic access
4. Cost tracking requires explicit API call instrumentation

For interactive research in Claude Desktop/Code, users can additionally configure the Exa MCP server (see vendor docs).

---

## 2. Technical Specification

### 2.1 Module Structure

```
src/kalshi_research/
├── exa/
│   ├── __init__.py
│   ├── client.py           # ExaClient (async, typed)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── search.py       # SearchRequest, SearchResult, SearchResponse
│   │   ├── contents.py     # ContentsRequest, ContentResult, ContentsResponse
│   │   ├── similar.py      # FindSimilarRequest, FindSimilarResponse
│   │   ├── answer.py       # AnswerRequest, AnswerResponse, Citation
│   │   └── research.py     # ResearchTask, ResearchStatus, ResearchOutput
│   ├── config.py           # ExaConfig (API key, base URL, timeouts)
│   └── exceptions.py       # ExaAPIError, ExaRateLimitError, ExaAuthError
tests/
├── unit/
│   └── exa/
│       ├── conftest.py     # respx fixtures, mock response factories
│       ├── test_client.py  # Client behavior tests
│       └── test_models.py  # Pydantic model validation tests
```

### 2.2 Configuration

```python
# src/kalshi_research/exa/config.py
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
import os


@dataclass(frozen=True)
class ExaConfig:
    """Configuration for Exa API client."""

    api_key: str
    base_url: str = "https://api.exa.ai"
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    @classmethod
    def from_env(cls) -> ExaConfig:
        """Load configuration from environment variables.

        Required:
            EXA_API_KEY: Your Exa API key

        Optional:
            EXA_BASE_URL: Override base URL (default: https://api.exa.ai)
            EXA_TIMEOUT: Request timeout in seconds (default: 30)
        """
        api_key = os.environ.get("EXA_API_KEY")
        if not api_key:
            raise ValueError(
                "EXA_API_KEY environment variable is required. "
                "Get your API key at https://exa.ai"
            )

        return cls(
            api_key=api_key,
            base_url=os.environ.get("EXA_BASE_URL", "https://api.exa.ai"),
            timeout_seconds=float(os.environ.get("EXA_TIMEOUT", "30")),
        )
```

### 2.3 Pydantic Models

```python
# src/kalshi_research/exa/models/search.py
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SearchType(str, Enum):
    """Exa search type."""
    NEURAL = "neural"
    FAST = "fast"
    AUTO = "auto"
    DEEP = "deep"


class SearchCategory(str, Enum):
    """Exa search category filter."""
    RESEARCH_PAPER = "research paper"
    NEWS = "news"
    PDF = "pdf"
    GITHUB = "github"
    TWEET = "tweet"
    PERSONAL_SITE = "personal site"
    FINANCIAL_REPORT = "financial report"
    COMPANY = "company"  # Note: Limited filter support
    PEOPLE = "people"    # Note: Limited filter support, includeDomains=LinkedIn only


class SearchRequest(BaseModel):
    """Request body for /search endpoint."""

    model_config = ConfigDict(frozen=True)

    query: str
    type: SearchType = SearchType.AUTO
    additional_queries: list[str] | None = Field(default=None, alias="additionalQueries")  # Deep search only
    num_results: int = Field(default=10, ge=1, le=100, alias="numResults")
    include_domains: list[str] | None = Field(default=None, alias="includeDomains")
    exclude_domains: list[str] | None = Field(default=None, alias="excludeDomains")
    start_published_date: datetime | None = Field(default=None, alias="startPublishedDate")
    end_published_date: datetime | None = Field(default=None, alias="endPublishedDate")
    include_text: list[str] | None = Field(default=None, alias="includeText")
    exclude_text: list[str] | None = Field(default=None, alias="excludeText")
    category: SearchCategory | None = None

    # Content retrieval options (inline with search)
    text: bool | dict[str, int] = False
    highlights: bool | dict[str, int] = False
    summary: bool | dict[str, str] = False
    context: bool | dict[str, int] = False  # RAG-optimized combined content


class SearchResult(BaseModel):
    """Individual search result."""

    model_config = ConfigDict(frozen=True)

    id: str
    url: str
    title: str
    published_date: datetime | None = Field(default=None, alias="publishedDate")
    author: str | None = None
    image: str | None = None
    favicon: str | None = None

    # Content fields (present if requested)
    text: str | None = None
    summary: str | None = None
    highlights: list[str] | None = None
    highlight_scores: list[float] | None = Field(default=None, alias="highlightScores")


class CostDollars(BaseModel):
    """Cost information from Exa API."""

    model_config = ConfigDict(frozen=True)

    total: float


class SearchResponse(BaseModel):
    """Response from /search endpoint."""

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(alias="requestId")
    results: list[SearchResult]
    search_type: str = Field(alias="searchType")
    context: str | None = None  # Combined content for RAG (if context=True in request)
    cost_dollars: CostDollars | None = Field(default=None, alias="costDollars")
```

```python
# src/kalshi_research/exa/models/answer.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Citation(BaseModel):
    """Citation from Answer endpoint."""

    model_config = ConfigDict(frozen=True)

    id: str
    url: str
    title: str
    author: str | None = None
    published_date: str | None = Field(default=None, alias="publishedDate")
    text: str | None = None


class AnswerRequest(BaseModel):
    """Request body for /answer endpoint."""

    model_config = ConfigDict(frozen=True)

    query: str
    stream: bool = False
    text: bool = False  # Include full text in citations


class AnswerResponse(BaseModel):
    """Response from /answer endpoint."""

    model_config = ConfigDict(frozen=True)

    answer: str
    citations: list[Citation]
    cost_dollars: dict[str, float] | None = Field(default=None, alias="costDollars")
```

```python
# src/kalshi_research/exa/models/research.py
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResearchModel(str, Enum):
    """Exa research model tiers."""
    FAST = "exa-research-fast"
    STANDARD = "exa-research"
    PRO = "exa-research-pro"


class ResearchStatus(str, Enum):
    """Research task status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"


class ResearchRequest(BaseModel):
    """Request body for /research/v1 endpoint."""

    model_config = ConfigDict(frozen=True)

    instructions: str = Field(max_length=4096)
    model: ResearchModel = ResearchModel.STANDARD
    output_schema: dict[str, Any] | None = Field(default=None, alias="outputSchema")


class ResearchOutput(BaseModel):
    """Output from completed research task."""

    model_config = ConfigDict(frozen=True)

    content: str
    parsed: dict[str, Any] | None = None  # Present if outputSchema was provided


class ResearchTask(BaseModel):
    """Research task response."""

    model_config = ConfigDict(frozen=True)

    research_id: str = Field(alias="researchId")
    status: ResearchStatus
    created_at: int = Field(alias="createdAt")
    model: str
    instructions: str
    output: ResearchOutput | None = None
    cost_dollars: dict[str, float] | None = Field(default=None, alias="costDollars")
```

### 2.4 Client Implementation

```python
# src/kalshi_research/exa/client.py
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, AsyncIterator

import httpx
import structlog

from kalshi_research.exa.config import ExaConfig
from kalshi_research.exa.exceptions import (
    ExaAPIError,
    ExaAuthError,
    ExaRateLimitError,
)
from kalshi_research.exa.models import (
    AnswerRequest,
    AnswerResponse,
    ContentsRequest,
    ContentsResponse,
    FindSimilarRequest,
    FindSimilarResponse,
    ResearchRequest,
    ResearchTask,
    SearchRequest,
    SearchResponse,
)

if TYPE_CHECKING:
    from types import TracebackType

logger = structlog.get_logger()


class ExaClient:
    """
    Async client for Exa API.

    Use as an async context manager:

        async with ExaClient.from_env() as exa:
            results = await exa.search("prediction markets")

    Or manage lifecycle manually:

        exa = ExaClient.from_env()
        await exa.open()
        try:
            results = await exa.search("prediction markets")
        finally:
            await exa.close()
    """

    def __init__(self, config: ExaConfig) -> None:
        """Initialize client with configuration."""
        self._config = config
        self._client: httpx.AsyncClient | None = None

    @classmethod
    def from_env(cls) -> ExaClient:
        """Create client from environment variables."""
        return cls(ExaConfig.from_env())

    async def open(self) -> None:
        """Open the HTTP client."""
        if self._client is not None:
            return

        self._client = httpx.AsyncClient(
            base_url=self._config.base_url,
            headers={
                "x-api-key": self._config.api_key,
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(self._config.timeout_seconds),
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> ExaClient:
        """Enter async context manager."""
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        await self.close()

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client, raising if not initialized."""
        if self._client is None:
            raise RuntimeError(
                "ExaClient not initialized. Use 'async with ExaClient()' "
                "or call 'await client.open()' first."
            )
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
    ) -> dict:
        """Make an API request with retry logic."""
        last_exception: Exception | None = None

        for attempt in range(self._config.max_retries):
            try:
                response = await self.client.request(
                    method=method,
                    url=path,
                    json=json,
                )

                if response.status_code == 401:
                    raise ExaAuthError("Invalid API key")

                if response.status_code == 429:
                    retry_after = int(
                        response.headers.get("retry-after", self._config.retry_delay_seconds)
                    )
                    raise ExaRateLimitError(f"Rate limited. Retry after {retry_after}s")

                if response.status_code >= 400:
                    raise ExaAPIError(
                        f"API error {response.status_code}: {response.text}"
                    )

                return response.json()

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                if attempt < self._config.max_retries - 1:
                    await asyncio.sleep(
                        self._config.retry_delay_seconds * (attempt + 1)
                    )
                    logger.warning(
                        "Retrying Exa request",
                        path=path,
                        attempt=attempt + 1,
                        error=str(e),
                    )

        raise ExaAPIError(f"Request failed after {self._config.max_retries} attempts") from last_exception

    # ─────────────────────────────────────────────────────────────────
    # Search
    # ─────────────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        *,
        search_type: str = "auto",
        additional_queries: list[str] | None = None,  # Deep search only
        num_results: int = 10,
        text: bool = False,
        highlights: bool = False,
        summary: bool = False,
        context: bool = False,  # RAG-optimized combined content
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        category: str | None = None,
    ) -> SearchResponse:
        """
        Search the web using Exa's neural search.

        Args:
            query: Search query
            search_type: Search type (auto, neural, fast, deep)
            additional_queries: Extra query variations (deep search only)
            num_results: Number of results (1-100)
            text: Include full page text in results
            highlights: Include relevant snippets
            summary: Include LLM-generated summaries
            context: Return combined context string for RAG (often better than highlights)
            include_domains: Only search these domains
            exclude_domains: Exclude these domains
            category: Filter by category (news, research paper, tweet, etc.)

        Returns:
            SearchResponse with results

        Example:
            >>> results = await exa.search(
            ...     "prediction market regulation",
            ...     search_type="deep",
            ...     additional_queries=["prediction market law", "betting regulation"],
            ...     context=True,
            ...     category="news",
            ...     num_results=20,
            ... )
        """
        request = SearchRequest(
            query=query,
            numResults=num_results,
            text=text,
            highlights=highlights,
            summary=summary,
            includeDomains=include_domains,
            excludeDomains=exclude_domains,
            category=category,
        )

        data = await self._request(
            "POST",
            "/search",
            json=request.model_dump(by_alias=True, exclude_none=True),
        )

        return SearchResponse.model_validate(data)

    async def search_and_contents(
        self,
        query: str,
        *,
        num_results: int = 10,
        text: bool = True,
        highlights: bool = True,
        **kwargs,
    ) -> SearchResponse:
        """
        Convenience method: search with text and highlights enabled.

        This is the most common pattern for RAG workflows.
        """
        return await self.search(
            query,
            num_results=num_results,
            text=text,
            highlights=highlights,
            **kwargs,
        )

    # ─────────────────────────────────────────────────────────────────
    # Contents
    # ─────────────────────────────────────────────────────────────────

    async def get_contents(
        self,
        urls: list[str],
        *,
        text: bool = True,
        highlights: bool = False,
        summary: bool = False,
        livecrawl: str = "fallback",
    ) -> ContentsResponse:
        """
        Get clean, parsed content from URLs.

        Args:
            urls: List of URLs to fetch
            text: Include full page text
            highlights: Extract relevant snippets
            summary: Generate LLM summaries
            livecrawl: When to crawl live (never, fallback, preferred, always)

        Returns:
            ContentsResponse with results and status per URL
        """
        request = ContentsRequest(
            urls=urls,
            text=text,
            highlights=highlights,
            summary=summary,
            livecrawl=livecrawl,
        )

        data = await self._request(
            "POST",
            "/contents",
            json=request.model_dump(by_alias=True, exclude_none=True),
        )

        return ContentsResponse.model_validate(data)

    # ─────────────────────────────────────────────────────────────────
    # Find Similar
    # ─────────────────────────────────────────────────────────────────

    async def find_similar(
        self,
        url: str,
        *,
        num_results: int = 10,
        text: bool = False,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
    ) -> FindSimilarResponse:
        """
        Find pages semantically similar to a given URL.

        Args:
            url: Source URL to find similar pages for
            num_results: Number of results (1-100)
            text: Include full page text
            include_domains: Only search these domains
            exclude_domains: Exclude these domains

        Returns:
            FindSimilarResponse with similar pages
        """
        request = FindSimilarRequest(
            url=url,
            numResults=num_results,
            text=text,
            includeDomains=include_domains,
            excludeDomains=exclude_domains,
        )

        data = await self._request(
            "POST",
            "/findSimilar",
            json=request.model_dump(by_alias=True, exclude_none=True),
        )

        return FindSimilarResponse.model_validate(data)

    # ─────────────────────────────────────────────────────────────────
    # Answer
    # ─────────────────────────────────────────────────────────────────

    async def answer(
        self,
        query: str,
        *,
        text: bool = False,
    ) -> AnswerResponse:
        """
        Get an LLM-generated answer with citations.

        Args:
            query: The question to answer
            text: Include full text in citations

        Returns:
            AnswerResponse with answer and citations

        Example:
            >>> result = await exa.answer(
            ...     "What is the current status of polymarket regulation?",
            ...     text=True,
            ... )
            >>> print(result.answer)
            >>> for cite in result.citations:
            ...     print(f"  - {cite.title}: {cite.url}")
        """
        request = AnswerRequest(query=query, text=text)

        data = await self._request(
            "POST",
            "/answer",
            json=request.model_dump(by_alias=True, exclude_none=True),
        )

        return AnswerResponse.model_validate(data)

    # ─────────────────────────────────────────────────────────────────
    # Research (Async Deep Research)
    # ─────────────────────────────────────────────────────────────────

    async def create_research_task(
        self,
        instructions: str,
        *,
        model: str = "exa-research",
        output_schema: dict | None = None,
    ) -> ResearchTask:
        """
        Create an async research task.

        Args:
            instructions: Research instructions (max 4096 chars)
            model: Research model (exa-research-fast, exa-research, exa-research-pro)
            output_schema: Optional JSON schema for structured output

        Returns:
            ResearchTask with research_id and initial status
        """
        request = ResearchRequest(
            instructions=instructions,
            model=model,
            outputSchema=output_schema,
        )

        data = await self._request(
            "POST",
            "/research/v1",
            json=request.model_dump(by_alias=True, exclude_none=True),
        )

        return ResearchTask.model_validate(data)

    async def get_research_task(self, research_id: str) -> ResearchTask:
        """
        Get the status and results of a research task.

        Args:
            research_id: The research task ID

        Returns:
            ResearchTask with current status and output (if completed)
        """
        data = await self._request("GET", f"/research/v1/{research_id}")
        return ResearchTask.model_validate(data)

    async def wait_for_research(
        self,
        research_id: str,
        *,
        poll_interval: float = 5.0,
        timeout: float = 300.0,
    ) -> ResearchTask:
        """
        Poll a research task until completion.

        Args:
            research_id: The research task ID
            poll_interval: Seconds between polls
            timeout: Maximum wait time in seconds

        Returns:
            Completed ResearchTask

        Raises:
            TimeoutError: If task doesn't complete within timeout
        """
        import time
        start = time.monotonic()

        while True:
            task = await self.get_research_task(research_id)

            if task.status in (ResearchStatus.COMPLETED, ResearchStatus.FAILED, ResearchStatus.CANCELED):
                return task

            elapsed = time.monotonic() - start
            if elapsed >= timeout:
                raise TimeoutError(
                    f"Research task {research_id} did not complete within {timeout}s"
                )

            await asyncio.sleep(poll_interval)
```

### 2.5 Exceptions

```python
# src/kalshi_research/exa/exceptions.py
from __future__ import annotations


class ExaError(Exception):
    """Base exception for Exa API errors."""
    pass


class ExaAPIError(ExaError):
    """Generic API error."""
    pass


class ExaAuthError(ExaError):
    """Authentication error (invalid API key)."""
    pass


class ExaRateLimitError(ExaError):
    """Rate limit exceeded."""
    pass
```

---

## 3. Testing Strategy

### 3.1 Test Philosophy

Following the project's minimal-mocking philosophy:
- Mock only at HTTP boundary (using `respx`)
- Use real Pydantic models
- Test actual client behavior, not implementation details

### 3.2 Test Fixtures

```python
# tests/unit/exa/conftest.py
from __future__ import annotations

import pytest
import respx

from kalshi_research.exa.client import ExaClient
from kalshi_research.exa.config import ExaConfig


@pytest.fixture
def exa_config() -> ExaConfig:
    """Test configuration."""
    return ExaConfig(
        api_key="test-api-key",
        base_url="https://api.exa.ai",
    )


@pytest.fixture
def exa_client(exa_config: ExaConfig) -> ExaClient:
    """Client configured for testing."""
    return ExaClient(exa_config)


@pytest.fixture
def mock_exa_api() -> respx.MockRouter:
    """Respx mock router for Exa API."""
    with respx.mock(base_url="https://api.exa.ai") as router:
        yield router


# Response factories
def make_search_response(
    results: list[dict] | None = None,
    request_id: str = "test-request-id",
) -> dict:
    """Create a mock search response."""
    return {
        "requestId": request_id,
        "results": results or [
            {
                "id": "result-1",
                "url": "https://example.com/article",
                "title": "Test Article",
                "publishedDate": "2024-01-15T10:00:00Z",
                "text": "Article content...",
            }
        ],
        "searchType": "neural",
        "costDollars": {"total": 0.005},
    }


def make_answer_response(
    answer: str = "This is the answer.",
    citations: list[dict] | None = None,
) -> dict:
    """Create a mock answer response."""
    return {
        "answer": answer,
        "citations": citations or [
            {
                "id": "cite-1",
                "url": "https://example.com/source",
                "title": "Source Article",
            }
        ],
        "costDollars": {"total": 0.01},
    }
```

### 3.3 Client Tests

```python
# tests/unit/exa/test_client.py
from __future__ import annotations

import httpx
import pytest
import respx

from kalshi_research.exa.client import ExaClient
from kalshi_research.exa.config import ExaConfig
from kalshi_research.exa.exceptions import ExaAPIError, ExaAuthError, ExaRateLimitError

from .conftest import make_answer_response, make_search_response


class TestExaClientLifecycle:
    """Test client initialization and cleanup."""

    async def test_context_manager_opens_and_closes(
        self, exa_config: ExaConfig
    ) -> None:
        """Client should properly manage httpx client lifecycle."""
        client = ExaClient(exa_config)

        assert client._client is None

        async with client:
            assert client._client is not None
            assert isinstance(client._client, httpx.AsyncClient)

        assert client._client is None

    async def test_client_raises_if_not_initialized(
        self, exa_client: ExaClient
    ) -> None:
        """Accessing client property before init should raise."""
        with pytest.raises(RuntimeError, match="not initialized"):
            _ = exa_client.client


class TestExaSearch:
    """Test search endpoint."""

    @respx.mock
    async def test_search_basic(self, exa_config: ExaConfig) -> None:
        """Basic search returns parsed results."""
        respx.post("https://api.exa.ai/search").respond(
            json=make_search_response()
        )

        async with ExaClient(exa_config) as client:
            response = await client.search("prediction markets")

        assert response.request_id == "test-request-id"
        assert len(response.results) == 1
        assert response.results[0].title == "Test Article"
        assert response.results[0].url == "https://example.com/article"

    @respx.mock
    async def test_search_with_options(self, exa_config: ExaConfig) -> None:
        """Search respects all options."""
        route = respx.post("https://api.exa.ai/search").respond(
            json=make_search_response()
        )

        async with ExaClient(exa_config) as client:
            await client.search(
                "test query",
                num_results=20,
                text=True,
                include_domains=["example.com"],
                category="news",
            )

        # Verify request body
        request_body = route.calls.last.request.content
        import json
        body = json.loads(request_body)
        assert body["query"] == "test query"
        assert body["numResults"] == 20
        assert body["text"] is True
        assert body["includeDomains"] == ["example.com"]
        assert body["category"] == "news"


class TestExaAnswer:
    """Test answer endpoint."""

    @respx.mock
    async def test_answer_returns_citations(self, exa_config: ExaConfig) -> None:
        """Answer endpoint returns answer with citations."""
        respx.post("https://api.exa.ai/answer").respond(
            json=make_answer_response(
                answer="Prediction markets are...",
                citations=[
                    {"id": "c1", "url": "https://a.com", "title": "Article A"},
                    {"id": "c2", "url": "https://b.com", "title": "Article B"},
                ],
            )
        )

        async with ExaClient(exa_config) as client:
            response = await client.answer("What are prediction markets?")

        assert "Prediction markets" in response.answer
        assert len(response.citations) == 2
        assert response.citations[0].url == "https://a.com"


class TestExaErrorHandling:
    """Test error handling and retries."""

    @respx.mock
    async def test_auth_error_raises(self, exa_config: ExaConfig) -> None:
        """401 response raises ExaAuthError."""
        respx.post("https://api.exa.ai/search").respond(status_code=401)

        async with ExaClient(exa_config) as client:
            with pytest.raises(ExaAuthError, match="Invalid API key"):
                await client.search("test")

    @respx.mock
    async def test_rate_limit_raises(self, exa_config: ExaConfig) -> None:
        """429 response raises ExaRateLimitError."""
        respx.post("https://api.exa.ai/search").respond(
            status_code=429,
            headers={"retry-after": "60"},
        )

        async with ExaClient(exa_config) as client:
            with pytest.raises(ExaRateLimitError):
                await client.search("test")

    @respx.mock
    async def test_retries_on_network_error(self, exa_config: ExaConfig) -> None:
        """Client retries on network errors."""
        config = ExaConfig(
            api_key="test",
            max_retries=3,
            retry_delay_seconds=0.01,  # Fast retries for tests
        )

        # Fail twice, succeed on third
        route = respx.post("https://api.exa.ai/search").mock(
            side_effect=[
                httpx.ConnectError("Connection refused"),
                httpx.ConnectError("Connection refused"),
                httpx.Response(200, json=make_search_response()),
            ]
        )

        async with ExaClient(config) as client:
            response = await client.search("test")

        assert len(route.calls) == 3
        assert response.request_id == "test-request-id"
```

### 3.4 Model Tests

```python
# tests/unit/exa/test_models.py
from __future__ import annotations

import pytest
from pydantic import ValidationError

from kalshi_research.exa.models.search import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchType,
)


class TestSearchModels:
    """Test search request/response models."""

    def test_search_request_defaults(self) -> None:
        """SearchRequest has sensible defaults."""
        req = SearchRequest(query="test")

        assert req.query == "test"
        assert req.type == SearchType.AUTO
        assert req.num_results == 10
        assert req.text is False

    def test_search_request_validation(self) -> None:
        """SearchRequest validates num_results bounds."""
        with pytest.raises(ValidationError):
            SearchRequest(query="test", numResults=0)

        with pytest.raises(ValidationError):
            SearchRequest(query="test", numResults=101)

    def test_search_response_parsing(self) -> None:
        """SearchResponse parses from API JSON."""
        data = {
            "requestId": "req-123",
            "results": [
                {
                    "id": "r1",
                    "url": "https://example.com",
                    "title": "Example",
                    "publishedDate": "2024-01-15T10:00:00Z",
                }
            ],
            "searchType": "neural",
        }

        response = SearchResponse.model_validate(data)

        assert response.request_id == "req-123"
        assert len(response.results) == 1
        assert response.results[0].published_date is not None

    def test_search_result_optional_fields(self) -> None:
        """SearchResult handles missing optional fields."""
        result = SearchResult(
            id="r1",
            url="https://example.com",
            title="Example",
        )

        assert result.text is None
        assert result.highlights is None
        assert result.author is None
```

---

## 4. Implementation Tasks

### Phase 1: Foundation (Test-First)

- [ ] Create `src/kalshi_research/exa/` package structure
- [ ] Write test fixtures in `tests/unit/exa/conftest.py`
- [ ] Write model tests (`test_models.py`)
- [ ] Implement Pydantic models (search, contents, answer, research)
- [ ] Run tests, verify models pass

### Phase 2: Client Core

- [ ] Write client lifecycle tests
- [ ] Implement `ExaConfig` and `ExaClient` skeleton
- [ ] Write search endpoint tests
- [ ] Implement `search()` method
- [ ] Write answer endpoint tests
- [ ] Implement `answer()` method

### Phase 3: Full API Coverage

- [ ] Write contents endpoint tests
- [ ] Implement `get_contents()` method
- [ ] Write find_similar endpoint tests
- [ ] Implement `find_similar()` method
- [ ] Write research endpoint tests
- [ ] Implement `create_research_task()`, `get_research_task()`, `wait_for_research()`

### Phase 4: Error Handling & Polish

- [ ] Write error handling tests (auth, rate limit, retries)
- [ ] Implement retry logic with exponential backoff
- [ ] Add structured logging throughout
- [ ] Update `pyproject.toml` with `exa_py` as optional dependency
- [ ] Add Exa config to `.env.example`

---

## 5. Acceptance Criteria

1. **Type Safety**: All methods have full type hints, passes mypy strict
2. **Test Coverage**: >90% coverage on exa/ module
3. **Error Handling**: Proper exceptions for auth, rate limit, network errors
4. **Documentation**: Docstrings on all public methods with examples
5. **Integration Ready**: Can be used by downstream specs (SPEC-021 through SPEC-024)

---

## 6. Configuration Updates

### .env.example additions

```bash
# Exa API (optional - enables AI-powered research features)
EXA_API_KEY=your-exa-api-key
# EXA_BASE_URL=https://api.exa.ai  # Optional override
# EXA_TIMEOUT=30                    # Optional timeout override
```

### pyproject.toml additions

```toml
[project.optional-dependencies]
research = [
    "exa_py>=1.0.0",  # Official SDK (optional, we use direct httpx)
]
```

---

## 7. See Also

- [SPEC-021: Exa-Powered Market Research](SPEC-021-exa-market-research.md)
- [SPEC-022: Exa News & Sentiment Pipeline](SPEC-022-exa-news-sentiment.md)
- [SPEC-023: Exa-Thesis Integration](SPEC-023-exa-thesis-integration.md)
- [SPEC-024: Exa Research Agent](SPEC-024-exa-research-agent.md)
- [Exa API Reference](../_vendor-docs/exa-api-reference.md)
