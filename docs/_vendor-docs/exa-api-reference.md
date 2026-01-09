# Exa API Reference (2026)

**Source:** [docs.exa.ai](https://docs.exa.ai)
**Python SDK:** `pip install exa_py` or `uv add exa_py`
**Last Verified:** 2026-01-08

---

## Overview

Exa is "a search engine made for AIs" - optimized for RAG, agentic workflows, and structured data extraction. Core capabilities:

- **Search**: Neural/embeddings-based web search
- **Contents**: Clean, parsed HTML/text from URLs
- **Find Similar**: Discover semantically related pages
- **Answer**: LLM-generated answers with citations
- **Research**: Async deep research with structured output

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

### Request Body

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | Required | The search query |
| `type` | enum | `"auto"` | `neural`, `fast`, `auto`, `deep` |
| `numResults` | integer | 10 | Max 100 results |
| `includeDomains` | string[] | - | Filter to specific domains (max 1200) |
| `excludeDomains` | string[] | - | Exclude domains (max 1200) |
| `startPublishedDate` | ISO 8601 | - | Filter by publish date |
| `endPublishedDate` | ISO 8601 | - | Filter by publish date |
| `startCrawlDate` | ISO 8601 | - | Filter by crawl date |
| `endCrawlDate` | ISO 8601 | - | Filter by crawl date |
| `includeText` | string[] | - | Must contain (1 string, 5 words max) |
| `excludeText` | string[] | - | Must not contain |
| `category` | enum | - | `research paper`, `news`, `pdf`, `github`, `company`, `people` |
| `userLocation` | string | - | Two-letter ISO country code |
| `moderation` | boolean | false | Filter unsafe content |
| `contents` | object | - | Control text/highlights/summary retrieval |

### Response

```json
{
  "requestId": "string",
  "results": [
    {
      "title": "string",
      "url": "string",
      "publishedDate": "string|null",
      "author": "string|null",
      "id": "string",
      "image": "string",
      "favicon": "string",
      "text": "string",
      "summary": "string",
      "highlights": ["string"],
      "highlightScores": [0.0]
    }
  ],
  "searchType": "neural|deep",
  "costDollars": { "total": 0.005 }
}
```

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
results = exa.search_and_contents("Latest research in LLMs", text=True)

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

### Request Body

| Parameter | Type | Description |
|-----------|------|-------------|
| `urls` | string[] | Required. URLs to crawl |
| `text` | boolean/object | Full page text. Object: `{maxCharacters, includeHtmlTags}` |
| `highlights` | object | Extract snippets: `{numSentences, highlightsPerUrl, query}` |
| `summary` | object | LLM summaries: `{query, schema}` |
| `livecrawl` | enum | `never`, `fallback`, `preferred`, `always` |
| `livecrawlTimeout` | integer | Milliseconds (default 10000) |
| `subpages` | integer | Number of subpages to crawl |
| `subpageTarget` | string/string[] | Keywords for subpage filtering |

### Response

```json
{
  "requestId": "string",
  "results": [
    {
      "title": "string",
      "url": "string",
      "publishedDate": "string|null",
      "author": "string|null",
      "text": "string",
      "highlights": ["string"],
      "summary": "string"
    }
  ],
  "statuses": [
    {
      "id": "string",
      "status": "success|error",
      "error": { "tag": "CRAWL_NOT_FOUND|CRAWL_TIMEOUT|SOURCE_NOT_AVAILABLE" }
    }
  ]
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

Find semantically related pages to a given URL.

### Request Body

| Parameter | Type | Description |
|-----------|------|-------------|
| `url` | string | Required. Source URL |
| `numResults` | integer | Max 100, default 10 |
| `includeDomains` | string[] | Limit to domains |
| `excludeDomains` | string[] | Exclude domains |
| `startPublishedDate` | ISO 8601 | Filter by date |
| `endPublishedDate` | ISO 8601 | Filter by date |

### Code Examples

**Python:**
```python
from exa_py import Exa

exa = Exa('YOUR_EXA_API_KEY')
results = exa.find_similar_and_contents(
    url="https://arxiv.org/abs/2307.06435",
    text=True
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
      "text": "string"
    }
  ],
  "costDollars": { "total": 0.005 }
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

## Research Endpoint

**POST** `/research/v1`

Async deep research with structured output support.

### Request Body

| Parameter | Type | Description |
|-----------|------|-------------|
| `instructions` | string | Required. Research guidelines (max 4096 chars) |
| `model` | enum | `exa-research-fast`, `exa-research`, `exa-research-pro` |
| `outputSchema` | object | JSON Schema for structured output |

### Response (201 Created)

```json
{
  "researchId": "string",
  "status": "pending|running|completed|canceled|failed",
  "createdAt": 1234567890,
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
    "parsed": {} // if outputSchema provided
  },
  "costDollars": { "total": 0.10 }
}
```

### Code Examples

**Python:**
```python
from exa_py import Exa

exa = Exa('YOUR_EXA_API_KEY')

# Create research task
task = exa.research.create_task(
    instructions="Summarize latest AI safety research",
    model="exa-research"
)

# Poll for results
result = exa.research.get_task(task.research_id)
```

---

## Python SDK Reference

### Installation

```bash
pip install exa_py
# or
uv add exa_py
```

### Quick Start

```python
from exa_py import Exa

# Initialize client
exa = Exa('YOUR_EXA_API_KEY')

# Search with contents
results = exa.search_and_contents(
    query="prediction markets research",
    num_results=10,
    text=True,
    highlights=True
)

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
| `search(query, **kwargs)` | Search without contents |
| `search_and_contents(query, **kwargs)` | Search with text/highlights/summary |
| `get_contents(urls, **kwargs)` | Get contents from URLs |
| `find_similar(url, **kwargs)` | Find similar pages |
| `find_similar_and_contents(url, **kwargs)` | Find similar with contents |
| `answer(query, **kwargs)` | Get LLM answer with citations |
| `research.create_task(instructions, **kwargs)` | Start async research |
| `research.get_task(research_id)` | Get research results |

---

## Pricing (as of 2026)

| Operation | Cost |
|-----------|------|
| Neural Search (1-25 results) | $0.005 |
| Neural Search (26-100 results) | $0.025 |
| Deep Search (1-25 results) | $0.015 |
| Content Text (per page) | $0.001 |
| Content Highlight (per page) | $0.001 |
| Content Summary (per page) | $0.001 |

---

## Tool Use with Claude

Exa can be used as a tool with Claude for agentic research workflows:

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
        results = exa.search_and_contents(
            tool_input["query"],
            num_results=5,
            text=True
        )
        return "\n\n".join([
            f"**{r.title}**\n{r.url}\n{r.text[:500]}"
            for r in results.results
        ])
```

---

## See Also

- [Kalshi API Reference](kalshi-api-reference.md) - Kalshi prediction market API
- [Architecture](../architecture/overview.md) - How our codebase integrates external APIs
