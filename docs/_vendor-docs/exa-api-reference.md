# Exa API Reference (2026)

**Source:** [docs.exa.ai](https://docs.exa.ai)
**OpenAPI Spec:** [exa-openapi-spec.yaml](https://raw.githubusercontent.com/exa-labs/openapi-spec/refs/heads/master/exa-openapi-spec.yaml)
**Python SDK:** `pip install exa-py` / `pip install exa_py` (module: `exa_py`)
**Last Verified:** 2026-01-10
**MCP Server:** `npx exa-mcp-server` or hosted at `https://mcp.exa.ai/mcp`
**Verified Against:** OpenAPI spec v1.2.0, `exa-py` v2.0.2, `exa-mcp-server` v3.1.3

---

## Overview

Exa is "a search engine made for AIs" - optimized for RAG, agentic workflows, and structured data extraction. Unlike traditional search engines (optimized for human clicks), Exa is optimized for machine consumption.

**Core Capabilities:**

- **Search**: Neural/embeddings-based web search with 4 modes (auto, neural, fast, deep)
- **Contents**: Clean, parsed text from URLs with live crawling
- **Find Similar**: Discover semantically related pages
- **Answer**: LLM-generated answers with citations
- **Research**: Async deep research with structured output (agentic)
- **MCP Server**: Native integration with Claude and other MCP-compatible agents

---

## Base URL & Authentication

**Base URL:** `https://api.exa.ai`

**Authentication:**
```
x-api-key: YOUR_EXA_API_KEY
```

Or use Bearer token:
```
Authorization: Bearer YOUR_EXA_API_KEY
```

---

## Search Endpoint

**POST** `/search`

Intelligently find webpages using embeddings-based search.

### Search Types

| Type | Description |
|------|-------------|
| `auto` | **Default.** Intelligently selects the best method |
| `neural` | Embeddings-based semantic search |
| `fast` | Streamlined search optimized for speed |
| `deep` | Multi-pass with query expansion for highest quality |

**When to use `deep`:** Complex research queries where quality matters more than speed. The endpoint agentically searches, processes, and searches again until it finds the highest quality information.

### Request Body

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | Required | The search query |
| `type` | enum | `"auto"` | `auto`, `neural`, `fast`, `deep` |
| `additionalQueries` | string[] | - | Extra query variations (**deep search only**) |
| `numResults` | integer | 10 | Max 100 results |
| `includeDomains` | string[] | - | Filter to specific domains |
| `excludeDomains` | string[] | - | Exclude domains |
| `startPublishedDate` | ISO 8601 | - | Filter by publish date |
| `endPublishedDate` | ISO 8601 | - | Filter by publish date |
| `startCrawlDate` | ISO 8601 | - | Filter by crawl date |
| `endCrawlDate` | ISO 8601 | - | Filter by crawl date |
| `includeText` | string[] | - | Must contain (1 string, 5 words max) |
| `excludeText` | string[] | - | Must not contain (1 string, 5 words max; checks first 1,000 words) |
| `category` | enum | - | See category table below |
| `userLocation` | string | - | Two-letter ISO country code |
| `moderation` | boolean | false | Moderate results for safety (SDK) |
| `flags` | string[] | - | Experimental flags (SDK) |
| `context` | boolean/object | - | Return combined context string for RAG |
| `contents` | object | - | Control text/highlights/summary retrieval |

### Categories

| Category | Description |
|----------|-------------|
| `news` | News articles |
| `research paper` | Academic papers |
| `pdf` | PDF documents |
| `github` | GitHub repositories |
| `tweet` | Twitter/X posts |
| `personal site` | Personal websites/blogs |
| `financial report` | Financial documents |
| `company` | Company profiles |
| `people` | People profiles |

> **Notes:** The official `exa-py` SDK exposes `moderation` and `flags`, but they are not currently documented in `exa-openapi-spec.yaml` v1.2.0. Prefer treating them as optional/experimental until confirmed in vendor docs.

### Response

```json
{
  "requestId": "string",
  "results": [
    {
      "id": "string",
      "title": "string",
      "url": "string",
      "publishedDate": "string|null",
      "author": "string|null",
      "score": 0.0,
      "image": "string|null",
      "favicon": "string|null",
      "text": "string",
      "summary": "string",
      "highlights": ["string"],
      "highlightScores": [0.0]
    }
  ],
  "context": "string (combined content for RAG, if requested)",
  "searchType": "string",
  "costDollars": {
    "total": 0.005,
    "breakDown": [
      {
        "search": 0.005,
        "contents": 0.0,
        "breakdown": {
          "neuralSearch": 0.005,
          "deepSearch": 0.0,
          "contentText": 0.0,
          "contentHighlight": 0.0,
          "contentSummary": 0.0
        }
      }
    ],
    "perRequestPrices": {
      "neuralSearch_1_25_results": 0.005,
      "neuralSearch_26_100_results": 0.025,
      "deepSearch_1_25_results": 0.015,
      "deepSearch_26_100_results": 0.075
    },
    "perPagePrices": {
      "contentText": 0.001,
      "contentHighlight": 0.001,
      "contentSummary": 0.001
    }
  }
}
```

> **Note:** `searchType` indicates which search method was used. For `type="auto"`, this shows the actual method selected (e.g., "neural" or "deep").

> **Contents note:** You may see `text: true` used at the top level in examples; the official SDKs send content options under `contents` (e.g. `contents: {"text": true}`), which supports advanced options like `highlights`, `summary`, `subpages`, and `extras`.

### Code Examples

**cURL:**
```bash
curl -X POST 'https://api.exa.ai/search' \
  -H 'x-api-key: YOUR_EXA_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"query": "Latest research in LLMs", "text": true}'
```

**Python:**
```python
from exa_py import Exa

exa = Exa('YOUR_EXA_API_KEY')
results = exa.search("Latest research in LLMs", num_results=10, contents={"text": True})

for result in results.results:
    print(f"{result.title}: {result.url}")
```

**JavaScript:**
```javascript
import Exa from 'exa-js';
const exa = new Exa('YOUR_EXA_API_KEY');

const results = await exa.searchAndContents('Latest research in LLMs', { text: true });
```

---

## Contents Endpoint

**POST** `/contents`

Obtain clean, parsed content from URLs with automatic live crawling fallback.

### Livecrawl Options

| Option | Description |
|--------|-------------|
| `never` | Disable live crawling (use cache only) |
| `fallback` | Livecrawl only when cache is empty |
| `preferred` | **Recommended.** Try livecrawl first, fall back to cache if crawling fails |
| `always` | Always live-crawl (not recommended without consulting Exa) |
| `auto` | Let Exa choose behavior (SDK) |

### Request Body

| Parameter | Type | Description |
|-----------|------|-------------|
| `urls` | string[] | Required. URLs to crawl |
| `ids` | string[] | **Deprecated.** Use `urls` instead |
| `text` | boolean/object | Full page text. Object: `{maxCharacters, includeHtmlTags}` |
| `highlights` | object | Extract snippets: `{query, numSentences, highlightsPerUrl}` |
| `summary` | object | LLM summaries: `{query, schema}` for structured output |
| `metadata` | boolean/object | Request metadata (SDK) |
| `livecrawl` | enum | `never`, `fallback`, `preferred`, `always`, `auto` |
| `livecrawlTimeout` | integer | Milliseconds (default 10000) |
| `filterEmptyResults` | boolean | Drop empty results (SDK) |
| `subpages` | integer | Number of subpages to crawl |
| `subpageTarget` | string/string[] | Keywords for subpage filtering |
| `extras` | object | Additional data: `{links: N, imageLinks: N}` |
| `flags` | string[] | Experimental flags (SDK) |
| `context` | boolean/object | Return combined context string for RAG |

### Response

```json
{
  "requestId": "string",
  "results": [
    {
      "id": "string",
      "title": "string",
      "url": "string",
      "publishedDate": "string|null",
      "author": "string|null",
      "score": 0.0,
      "image": "string|null",
      "favicon": "string|null",
      "text": "string",
      "highlights": ["string"],
      "highlightScores": [0.0],
      "summary": "string",
      "subpages": [],
      "extras": {"links": [], "imageLinks": []}
    }
  ],
  "statuses": [
    {
      "id": "string",
      "status": "success|error",
      "error": {
        "tag": "CRAWL_NOT_FOUND|CRAWL_TIMEOUT|CRAWL_LIVECRAWL_TIMEOUT|SOURCE_NOT_AVAILABLE|CRAWL_UNKNOWN_ERROR",
        "httpStatusCode": 404
      }
    }
  ],
  "context": "string (combined content for RAG, if requested)",
  "costDollars": {
    "total": 0.001,
    "perPagePrices": {
      "contentText": 0.001,
      "contentHighlight": 0.001,
      "contentSummary": 0.001
    }
  }
}
```

### Code Examples

**Python:**
```python
from exa_py import Exa

exa = Exa('YOUR_EXA_API_KEY')
results = exa.get_contents(
    urls=["https://arxiv.org/abs/2307.06435"],
    text=True
)
```

---

## Find Similar Endpoint

**POST** `/findSimilar`

Find semantically related pages to a given URL. Supports the same filtering options as Search.

### Request Body

| Parameter | Type | Description |
|-----------|------|-------------|
| `url` | string | Required. Source URL to find similar pages for |
| `numResults` | integer | Max 100, default 10 |
| `includeDomains` | string[] | Limit to domains |
| `excludeDomains` | string[] | Exclude domains |
| `startPublishedDate` | ISO 8601 | Filter by publish date |
| `endPublishedDate` | ISO 8601 | Filter by publish date |
| `startCrawlDate` | ISO 8601 | Filter by crawl date |
| `endCrawlDate` | ISO 8601 | Filter by crawl date |
| `includeText` | string[] | Must contain (1 string, 5 words max) |
| `excludeText` | string[] | Must not contain (1 string, 5 words max; checks first 1,000 words) |
| `excludeSourceDomain` | boolean | Exclude results from the source URL's domain (SDK) |
| `category` | enum | A data category to focus on (SDK) |
| `flags` | string[] | Experimental flags (SDK) |
| `context` | boolean/object | Return combined context string for RAG |
| `contents` | object | Configure text/highlights/summary retrieval |

### Response

```json
{
  "requestId": "string",
  "results": [
    {
      "id": "string",
      "title": "string",
      "url": "string",
      "publishedDate": "string|null",
      "author": "string|null",
      "score": 0.0,
      "image": "string|null",
      "favicon": "string|null",
      "text": "string",
      "summary": "string",
      "highlights": ["string"],
      "highlightScores": [0.0]
    }
  ],
  "context": "string (combined content for RAG, if requested)",
  "costDollars": {
    "total": 0.005
  }
}
```

### Code Examples

**Python:**
```python
from exa_py import Exa

exa = Exa('YOUR_EXA_API_KEY')
results = exa.find_similar(
    "https://arxiv.org/abs/2307.06435",
    num_results=10,
    contents={"text": True},
)
```

---

## Answer Endpoint

**POST** `/answer`

Generate LLM-powered answers with citations from web search.

### Request Body

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | Required | The question to answer |
| `stream` | boolean | false | Server-sent events stream |
| `text` | boolean | false | Include full text in citations |

### Response

```json
{
  "answer": "string - generated answer",
  "citations": [
    {
      "id": "string",
      "url": "string",
      "title": "string",
      "author": "string|null",
      "publishedDate": "string|null",
      "image": "string|null",
      "favicon": "string|null",
      "text": "string"
    }
  ],
  "costDollars": {
    "total": 0.005,
    "breakDown": [
      {
        "search": 0.005,
        "contents": 0.0,
        "breakdown": {
          "neuralSearch": 0.005,
          "deepSearch": 0.0,
          "contentText": 0.0,
          "contentHighlight": 0.0,
          "contentSummary": 0.0
        }
      }
    ]
  }
}
```

### Code Examples

**Python:**
```python
from exa_py import Exa

exa = Exa('YOUR_EXA_API_KEY')
result = exa.answer(
    "What is the latest valuation of SpaceX?",
    text=True
)

print(result.answer)
for citation in result.citations:
    print(f"  - {citation.title}: {citation.url}")
```

---

## Research Endpoints

- **GET** `/research/v1` (list)
- **POST** `/research/v1` (create)
- **GET** `/research/v1/{researchId}` (get / stream)

Async deep research with structured output support.

### Create Request Body

| Parameter | Type | Description |
|-----------|------|-------------|
| `instructions` | string | Required. Research guidelines (max 4096 chars) |
| `model` | enum | `exa-research-fast`, `exa-research`, `exa-research-pro` (SDK default: `exa-research-fast`; OpenAPI spec v1.2.0 documents `exa-research`/`exa-research-pro`) |
| `outputSchema` | object | JSON Schema for structured output |

### Get Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `stream` | boolean | false | Stream Server-Sent Events (SSE) |
| `events` | boolean | false | Include `events` in non-streaming responses |

### Response (create: 201)

```json
{
  "researchId": "string",
  "status": "pending|running|completed|canceled|failed",
  "createdAt": 1234567890123,
  "model": "exa-research",
  "instructions": "string"
}
```

When completed:
```json
{
  "researchId": "string",
  "status": "completed",
  "output": {
    "content": "string - research results",
    "parsed": {}
  },
  "costDollars": {
    "total": 0.10,
    "numSearches": 6,
    "numPages": 20,
    "reasoningTokens": 1000
  }
}
```

> **Note:** When you provide `outputSchema`, the response may include a structured `output.parsed` in addition to `output.content`.

### Code Examples

**Python:**
```python
from exa_py import Exa

exa = Exa('YOUR_EXA_API_KEY')

# Create research task
research = exa.research.create(
    instructions="Summarize latest AI safety research",
    model="exa-research"
)

# Poll for results
result = exa.research.poll_until_finished(research.research_id)
```

---

## Python SDK Reference

### Installation

```bash
pip install exa-py
# or
uv add exa-py
```

### Quick Start

```python
from exa_py import Exa

# Initialize client
exa = Exa('YOUR_EXA_API_KEY')

# Search (returns text contents by default)
results = exa.search("prediction markets research", num_results=10)

# Access results
for r in results.results:
    print(f"Title: {r.title}")
    print(f"URL: {r.url}")
    print(f"Text: {r.text[:200]}...")
    print()
```

### Available Methods

| Method | Description |
|--------|-------------|
| `search(query, **kwargs)` | Search (returns text contents by default; use `contents=False` to disable) |
| `search_and_contents(query, **kwargs)` | Deprecated; prefer `search(query, contents=...)` |
| `get_contents(urls, **kwargs)` | Get contents from URLs |
| `find_similar(url, **kwargs)` | Find similar pages |
| `find_similar_and_contents(url, **kwargs)` | Deprecated; prefer `find_similar(url, contents=...)` |
| `answer(query, **kwargs)` | Get LLM answer with citations |
| `stream_answer(query, **kwargs)` | Streaming answer (yields chunks) |
| `research.create(instructions=..., **kwargs)` | Start async research |
| `research.get(research_id, **kwargs)` | Get research results |
| `research.list(cursor=..., limit=...)` | List research tasks |
| `research.poll_until_finished(research_id, **kwargs)` | Poll for completion |

> **Note:** Structured summaries using `summary={"schema": {...}}` return JSON strings that require parsing.

---

## Pricing (as of 2026)

See [Exa Pricing](https://exa.ai/pricing) for current free credits and plan limits.

### Search Pricing (per 1,000 requests)

| Search Type | 1-25 results | 26-100 results |
|-------------|--------------|----------------|
| Fast/Auto/Neural | $5 | $25 |
| Deep | $15 | $75 |

### Contents Pricing (per 1,000 pages)

| Content Type | Cost |
|--------------|------|
| Text | $1 |
| Highlights | $1 |
| Summary | $1 |

### Answer Pricing

The Answer endpoint returns `costDollars` in the response. Use `costDollars.total` as the source of truth.

### Research API Pricing (Variable)

Research API uses consumption-based billing. You're only charged for tasks that complete successfully.

| Component | exa-research | exa-research-pro |
|-----------|--------------|------------------|
| Agent searches (per 1k) | $5 | $5 |
| Agent page reads (per 1k pages*) | $5 | $10 |
| Reasoning tokens (per 1M) | $5 | $5 |

*Page = 1,000 tokens of webpage content

**Typical task cost:** $0.10-$0.50 depending on complexity (20-40 second completion)

---

## MCP Server (Model Context Protocol)

Exa provides an official MCP server for native integration with Claude Desktop, Claude Code, Cursor, and other MCP-compatible agents. This eliminates the need to write custom tool wrappers.

### Installation Options

**Option 1: NPX (Local)**
```bash
npx exa-mcp-server
```

**Option 2: Hosted Server**
```
https://mcp.exa.ai/mcp
```

### Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "exa": {
      "command": "npx",
      "args": ["-y", "exa-mcp-server"],
      "env": {
        "EXA_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Claude Code / Cursor Configuration (HTTP)

```json
{
  "mcpServers": {
    "exa": {
      "type": "http",
      "url": "https://mcp.exa.ai/mcp"
    }
  }
}
```

### Available MCP Tools

By default, only `web_search_exa` and `get_code_context_exa` are enabled. Enable additional tools via args:

| Tool | Description |
|------|-------------|
| `web_search_exa` | Real-time web search with content extraction |
| `deep_search_exa` | Higher-quality web search (slower / more expensive) |
| `get_code_context_exa` | Code snippets/docs from GitHub, StackOverflow |
| `crawling_exa` | Extract content from specific URLs |
| `company_research_exa` | Comprehensive company/business research |
| `linkedin_search_exa` | LinkedIn people/company search |
| `deep_researcher_start` | Start async research task |
| `deep_researcher_check` | Poll for research results |

**Enable all tools:**
```json
"args": ["-y", "exa-mcp-server", "tools=web_search_exa,deep_search_exa,get_code_context_exa,crawling_exa,company_research_exa,linkedin_search_exa,deep_researcher_start,deep_researcher_check"]
```

**Selective tools via hosted URL:**
```
https://mcp.exa.ai/mcp?tools=web_search_exa,company_research_exa
```

### When to Use MCP vs Direct SDK

| Use Case | Recommendation |
|----------|----------------|
| Interactive research with Claude | MCP Server |
| Jupyter notebooks | Python SDK |
| Production pipelines | Python SDK (typed, testable) |
| Quick prototyping | MCP Server |
| Custom structured output | Python SDK with `outputSchema` |

---

## Tool Use with Claude (Manual)

For custom tool definitions (when MCP is unavailable or you need fine-grained control):

```python
import anthropic
from exa_py import Exa

exa = Exa('YOUR_EXA_API_KEY')
client = anthropic.Anthropic()

# Define Exa as a tool
tools = [
    {
        "name": "web_search",
        "description": "Search the web for current information using Exa",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["query"]
        }
    }
]

# In your tool execution loop
def execute_tool(tool_name, tool_input):
    if tool_name == "web_search":
        results = exa.search(
            tool_input["query"],
            num_results=5,
            contents={"text": True},
        )
        return "\n\n".join([
            f"**{r.title}**\n{r.url}\n{r.text[:500]}"
            for r in results.results
        ])
```

---

## Integration Tips for Kalshi Research

### Event Resolution

When checking if a market resolved, use `category="news"` and date filters:

```python
# Find resolution sources for a market expiring this week
results = exa.search(
    "Federal Reserve interest rate decision January 2026",
    type="deep",  # Quality matters for resolution
    category="news",
    start_published_date="2026-01-06T00:00:00Z",
    include_domains=["federalreserve.gov", "reuters.com", "bloomberg.com"],
    contents={"text": True},
)
```

### Thesis Research

For creating trading theses, use the Research API with structured output:

```python
research = exa.research.create(
    instructions="""
    Analyze the likelihood of [EVENT] occurring by [DATE].

    Research:
    1. Historical precedent
    2. Current indicators
    3. Expert opinions
    4. Contrarian arguments

    Provide a probability estimate with confidence interval.
    """,
    model="exa-research",
    output_schema={
        "type": "object",
        "properties": {
            "probability": {"type": "number"},
            "confidence_low": {"type": "number"},
            "confidence_high": {"type": "number"},
            "bull_case": {"type": "string"},
            "bear_case": {"type": "string"},
            "key_sources": {"type": "array", "items": {"type": "string"}}
        }
    }
)
```

### News Monitoring

For sentiment analysis and news tracking:

```python
# Find recent news about tracked markets
results = exa.search(
    "Bitcoin ETF SEC approval 2026",
    type="auto",
    category="news",
    start_published_date="2026-01-01T00:00:00Z",
    num_results=20,
    contents={
        "text": True,
        "highlights": {"num_sentences": 3, "highlights_per_url": 2},
    },
)
```

### Domain Filtering for Resolution Sources

When a Kalshi market specifies a "Resolution Source", use `include_domains`:

```python
# Market resolves based on BLS data
results = exa.search(
    "unemployment rate January 2026",
    include_domains=["bls.gov"],
    contents={
        "text": True,
        "livecrawl": "preferred",  # Get fresh data
    },
)
```

---

## See Also

- [Kalshi API Reference](kalshi-api-reference.md) - Kalshi prediction market API
- [Architecture](../architecture/overview.md) - How our codebase integrates external APIs
- [Exa MCP Server (GitHub)](https://github.com/exa-labs/exa-mcp-server) - Official MCP server
- [Exa Pricing](https://exa.ai/pricing) - Current pricing details
