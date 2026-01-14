# DEBT-026: Missing Function Docstrings

**Priority:** P4 (Cosmetic/Quality)
**Status:** ✅ Resolved
**Found:** 2026-01-14
**Fixed:** 2026-01-14
**Source:** CodeRabbit pre-merge check (42.97% docstring coverage)

---

## Summary

Resolved by adding docstrings to all previously-missing public module/class callables (43 across 16
files). This improves discoverability and IDE documentation popups.

---

## Impact

- **Severity:** Low - Does not affect functionality
- **User Impact:** Reduced IDE experience (no hover docs)
- **Maintainability:** Harder for new contributors to understand code

---

## Functions That Were Missing Docstrings (Fixed)

### High Priority: Exa Client (`src/kalshi_research/exa/client.py`)

| Callable | Specification |
|----------|--------------|
| `ExaClient.from_env()` | Create an `ExaClient` from environment variables via `ExaConfig.from_env()`. |
| `ExaClient.open()` | Initialize the internal `httpx.AsyncClient`. Safe to call multiple times. |
| `ExaClient.close()` | Close the internal `httpx.AsyncClient`. Safe to call multiple times. |
| `ExaClient.client` | Property returning the underlying `httpx.AsyncClient`. Raises `RuntimeError` if not initialized. |
| `ExaClient.search(...)` | Call Exa `/search`. Builds a `SearchRequest` (including optional `contents`) and returns `SearchResponse`. |
| `ExaClient.get_contents(...)` | Call Exa `/contents` for the given URLs. Returns `ContentsResponse`. |
| `ExaClient.find_similar(...)` | Call Exa `/findSimilar`. Returns `FindSimilarResponse`. |
| `ExaClient.answer(...)` | Call Exa `/answer`. Returns `AnswerResponse`. |
| `ExaClient.create_research_task(...)` | Create async deep research task via `POST /research/v1`. Returns a `ResearchTask` with `research_id`. |
| `ExaClient.get_research_task(research_id)` | Fetch status/results for a research task via `GET /research/v1/{research_id}`. Returns `ResearchTask`. |
| `ExaClient.list_research_tasks(...)` | List research tasks via `GET /research/v1` with pagination (`cursor`, `limit`). Raises `ValueError` if `limit` is out of bounds. |
| `ExaClient.wait_for_research(...)` | Poll `get_research_task()` until terminal status or timeout. Raises `TimeoutError` on timeout. |

### High Priority: Execution (`src/kalshi_research/execution/executor.py`)

| Callable | Specification |
|----------|--------------|
| `TradeExecutor.live` | Property returning whether this executor is in live-trading mode (vs dry-run). |
| `TradeExecutor.audit_log_path` | Property returning the JSONL audit log path. |
| `TradeExecutor.create_order(...)` | Create an order through the safety harness. Raises `TradeSafetyError` when checks fail; always writes an audit event. |

### Medium Priority: Analysis & News

#### `src/kalshi_research/analysis/liquidity.py`

| Callable | Specification |
|----------|--------------|
| `OrderbookAnalyzer.depth(orderbook)` | Compute distance-weighted `DepthAnalysis` around the midpoint. |
| `OrderbookAnalyzer.slippage(orderbook, side, action, quantity=...)` | Estimate execution using book-walking. Returns `SlippageEstimate`. |
| `OrderbookAnalyzer.liquidity(market, orderbook)` | Compute composite liquidity metrics. Returns `LiquidityAnalysis`. |

#### `src/kalshi_research/news/aggregator.py`

| Callable | Specification |
|----------|--------------|
| `SentimentSummary.sentiment_label` | Map `avg_score` to a human-readable label ("Bullish", "Slightly Bullish", "Neutral", ...). |
| `SentimentSummary.trend_indicator` | Return "↑"/"↓"/"→" based on `score_change`, or "—" when no comparison is available. |
| `SentimentAggregator.get_market_summary(...)` | Aggregate stored article sentiment for a market over the last N days. Returns `SentimentSummary` or `None`. |
| `SentimentAggregator.get_event_summary(...)` | Aggregate stored article sentiment for an event over the last N days. Returns `SentimentSummary` or `None`. |

#### `src/kalshi_research/news/collector.py`

| Callable | Specification |
|----------|--------------|
| `ExaNewsClient.search_and_contents(...)` | Protocol: Exa search with contents enabled. Returns `SearchResponse`. |
| `NewsCollector.collect_for_tracked_item(tracked)` | Collect news for a single tracked market/event. Returns count of new articles inserted. |
| `NewsCollector.collect_all()` | Collect news for all active tracked items. Returns `{ticker: new_article_count}`. |

#### `src/kalshi_research/news/tracker.py`

| Callable | Specification |
|----------|--------------|
| `NewsTracker.track(...)` | Add or update a tracked market/event in the database. Returns the upserted `TrackedItem`. |
| `NewsTracker.untrack(ticker)` | Mark a tracked item inactive. Returns `True` if found, else `False`. |
| `NewsTracker.list_tracked(...)` | List tracked items from the database (optionally active-only). |

#### `src/kalshi_research/research/invalidation.py`

| Callable | Specification |
|----------|--------------|
| `InvalidationReport.has_high_severity` | Property returning `True` if any signal is `HIGH` severity. |
| `InvalidationDetector.check_thesis(thesis)` | Search recent news for contradicting signals. Returns `InvalidationReport`. |

#### `src/kalshi_research/research/thesis_research.py`

| Callable | Specification |
|----------|--------------|
| `ThesisResearcher.research_for_thesis(market, thesis_direction=...)` | Gather and classify evidence from Exa. Returns `ResearchedThesisData` (including estimated Exa cost). |
| `ThesisSuggester.suggest_theses(...)` | Generate lightweight thesis ideas from Exa search. Returns `list[ThesisSuggestion]`. |

#### `src/kalshi_research/research/topic.py`

| Callable | Specification |
|----------|--------------|
| `TopicResearcher.research_topic(topic, ...)` | Research a topic via Exa Answer + Search. Returns `TopicResearch` and tracks estimated Exa cost. |

### Low Priority: Internal Utilities

#### `src/kalshi_research/cli/utils.py`

| Callable | Specification |
|----------|--------------|
| `atomic_write_json(path, data)` | Write JSON atomically (temp file + fsync + rename). |
| `load_json_storage_file(...)` | Load/validate a JSON object with a required list key. Raises `typer.Exit(1)` on invalid JSON/schema. |

#### `src/kalshi_research/execution/audit.py`

| Callable | Specification |
|----------|--------------|
| `TradeAuditLogger.path` | Property returning the JSONL audit log path. |
| `TradeAuditLogger.write(event)` | Append one JSONL line for a `TradeAuditEvent`. Creates parent dir if needed. |

#### `src/kalshi_research/news/sentiment.py`

| Callable | Specification |
|----------|--------------|
| `SentimentAnalyzer.analyze(text, title=...)` | Keyword-based sentiment analysis for article text. Returns `SentimentResult`. |
| `SummarySentimentAnalyzer.analyze(url)` | Sentiment analysis using Exa summaries + a prompt. Returns `SentimentResult`. |

#### `src/kalshi_research/api/rate_limiter.py`

| Callable | Specification |
|----------|--------------|
| `RateLimiter.tier` | Property returning the configured `RateTier`. |

#### `src/kalshi_research/data/maintenance.py`

| Callable | Specification |
|----------|--------------|
| `PruneCounts.total_rows` | Property returning total rows represented by the prune counts. |

#### `src/kalshi_research/exa/models/answer.py` and `search.py`

| Callable | Specification |
|----------|--------------|
| `Citation.coerce_empty_published_date` | Validator converting empty-string `publishedDate` values to `None`. |
| `SearchResult.coerce_empty_published_date` | Validator converting empty-string `publishedDate` values to `None`. |

---

## Detection Script

To regenerate this list:

```python
import ast
from collections import defaultdict
from pathlib import Path

SKIP = {"__init__", "__aenter__", "__aexit__", "__post_init__", "__str__", "__repr__", "__eq__", "__hash__"}


def is_public(name: str) -> bool:
    return not name.startswith("_") and name not in SKIP


results = defaultdict(list)

for py_file in sorted(Path("src").rglob("*.py")):
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except SyntaxError:
        continue

    # Module-level callables
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if is_public(node.name) and not ast.get_docstring(node):
                results[str(py_file)].append(node.name)

        # Class methods/properties
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if is_public(item.name) and not ast.get_docstring(item):
                        results[str(py_file)].append(f"{node.name}.{item.name}")

for filepath, funcs in sorted(results.items(), key=lambda x: (-len(x[1]), x[0])):
    print(f"{filepath}: {', '.join(sorted(funcs))}")
```

---

## Docstring Format

Follow Google-style docstrings:

```python
def example_function(param1: str, param2: int) -> bool:
    """Brief one-line description.

    Longer explanation if needed, describing behavior,
    edge cases, or important notes.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: When param1 is empty.
    """
    ...
```

For simple functions, a one-liner is sufficient:

```python
def get_hours_left(self) -> float:
    """Calculate hours remaining until market close_time."""
    ...
```

---

## Notes

- All referenced modules already have module docstrings.
- The 42.97% coverage reported by CodeRabbit includes all functions (including private/nested ones).
- This debt is cosmetic and does not affect functionality
- Many missing docstrings were for simple properties where the name is self-documenting
