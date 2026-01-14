# DEBT-026: Missing Function Docstrings

**Status:** Open
**Priority:** P4 (Cosmetic/Quality)
**Created:** 2026-01-14
**Found by:** CodeRabbit pre-merge check (42.97% docstring coverage)
**Effort:** ~2-3 hours

---

## Summary

49 public functions/methods across 20 files are missing docstrings. This affects code
discoverability and IDE documentation popups.

---

## Impact

- **Severity:** Low - Does not affect functionality
- **User Impact:** Reduced IDE experience (no hover docs)
- **Maintainability:** Harder for new contributors to understand code

---

## Functions Needing Docstrings (with Specifications)

### High Priority: Exa Client (`src/kalshi_research/exa/client.py`)

| Function | Specification |
|----------|--------------|
| `from_env()` | Create ExaClient from environment variables (EXA_API_KEY). Returns: ExaClient instance. |
| `open()` | Initialize httpx.AsyncClient with configured headers/timeout. Must be called before requests. |
| `close()` | Close the httpx.AsyncClient and release resources. Safe to call multiple times. |
| `client` | Property returning the underlying httpx.AsyncClient. Raises RuntimeError if not initialized. |
| `search(query, ...)` | Search Exa's index for documents matching query. Returns: SearchResponse with results. |
| `get_contents(urls, ...)` | Fetch text/highlights/summary for given URLs. Returns: ContentsResponse. |
| `find_similar(url, ...)` | Find documents similar to the given URL. Returns: FindSimilarResponse. |
| `answer(query, ...)` | Get AI-generated answer for a question. Returns: AnswerResponse with citations. |
| `create_research_task(instructions, ...)` | Create async deep research task. Returns: ResearchTask with ID for polling. |
| `get_research_task(research_id)` | Fetch status/results of research task by ID. Returns: ResearchTask. |
| `list_research_tasks(cursor, limit)` | List research tasks with pagination. Returns: ResearchTaskListResponse. |
| `wait_for_research(research_id, ...)` | Poll until research task completes or times out. Returns: ResearchTask. |

### High Priority: Execution (`src/kalshi_research/execution/executor.py`)

| Function | Specification |
|----------|--------------|
| `live` | Property returning True if executing real orders (not paper trading). |
| `audit_log_path` | Property returning Path to the audit log file for this executor. |
| `create_order(...)` | Submit order to Kalshi. Validates against safety harness. Returns: Order result. |

### Medium Priority: Analysis & News

#### `src/kalshi_research/analysis/liquidity.py`

| Function | Specification |
|----------|--------------|
| `depth` | Calculate market depth at given price levels. Returns: depth metrics dict. |
| `slippage(side, quantity)` | Estimate price slippage for order of given size. Returns: estimated slippage in cents. |
| `liquidity` | Overall liquidity score combining depth, spread, and volume. Returns: LiquidityScore. |

#### `src/kalshi_research/news/aggregator.py`

| Function | Specification |
|----------|--------------|
| `sentiment_label(score)` | Convert numeric sentiment (-1 to 1) to label (Bearish/Neutral/Bullish). |
| `trend_indicator(change)` | Format trend as emoji indicator (↑/↓/→). |
| `get_market_summary(ticker, days)` | Aggregate sentiment data for market. Returns: MarketSentimentSummary or None. |
| `get_event_summary(event_ticker, days)` | Aggregate sentiment for event's markets. Returns: EventSentimentSummary or None. |

#### `src/kalshi_research/news/collector.py`

| Function | Specification |
|----------|--------------|
| `search_and_contents(query, ...)` | Search Exa and fetch content in one call. Returns: list of NewsItem. |
| `collect_for_tracked_item(item)` | Collect news for single tracked market/event. Returns: count of items collected. |
| `collect_all()` | Collect news for all tracked items. Returns: total count collected. |

#### `src/kalshi_research/news/tracker.py`

| Function | Specification |
|----------|--------------|
| `track(ticker, item_type)` | Add market/event to tracking list. Persists to JSON file. |
| `untrack(ticker)` | Remove item from tracking list. Returns: True if found and removed. |
| `list_tracked()` | List all tracked items. Returns: list of TrackedItem. |

#### `src/kalshi_research/research/invalidation.py`

| Function | Specification |
|----------|--------------|
| `has_high_severity` | Property returning True if any invalidation trigger is high severity. |
| `check_thesis(thesis)` | Check thesis against current market data for invalidation. Returns: InvalidationResult. |

#### `src/kalshi_research/research/thesis_research.py`

| Function | Specification |
|----------|--------------|
| `research_for_thesis(thesis)` | Run Exa deep research for thesis context. Returns: ResearchResult. |
| `suggest_theses(markets, ...)` | Generate thesis suggestions from market data. Returns: list of ThesisSuggestion. |

### Low Priority: Internal Utilities

#### `src/kalshi_research/cli/data.py`

| Function | Specification |
|----------|--------------|
| `sync_task` | Coroutine for background sync operation. Used by scheduler. |
| `snapshot_task` | Coroutine for background snapshot operation. Used by scheduler. |

#### `src/kalshi_research/cli/utils.py`

| Function | Specification |
|----------|--------------|
| `atomic_write_json(path, data)` | Write JSON atomically (write to temp, then rename). Prevents corruption. |
| `load_json_storage_file(path, kind, ...)` | Load JSON with validation and default structure. Returns: dict. |

#### `src/kalshi_research/data/scheduler.py`

| Function | Specification |
|----------|--------------|
| `runner` | Async task runner coroutine. Executes scheduled task at intervals. |

#### `src/kalshi_research/execution/audit.py`

| Function | Specification |
|----------|--------------|
| `path` | Property returning Path to audit log file. |
| `write(entry)` | Append audit entry to log file. Thread-safe via file locking. |

#### `src/kalshi_research/news/sentiment.py`

| Function | Specification |
|----------|--------------|
| `analyze(text)` | Analyze sentiment of text. Returns: SentimentResult with score and confidence. |

#### `src/kalshi_research/analysis/scanner.py`

| Function | Specification |
|----------|--------------|
| `get_hours_left` | Calculate hours remaining until market close_time. Returns: float. |

#### `src/kalshi_research/api/rate_limiter.py`

| Function | Specification |
|----------|--------------|
| `tier` | Property returning current rate limit tier (e.g., "standard", "elevated"). |

#### `src/kalshi_research/data/database.py`

| Function | Specification |
|----------|--------------|
| `set_sqlite_pragma` | Set SQLite pragmas for performance (WAL mode, synchronous, etc.). |

#### `src/kalshi_research/data/maintenance.py`

| Function | Specification |
|----------|--------------|
| `total_rows` | Count total rows across all tables. Returns: int total count. |

#### `src/kalshi_research/exa/models/answer.py` and `search.py`

| Function | Specification |
|----------|--------------|
| `coerce_empty_published_date` | Pydantic validator converting empty string publishedDate to None. |

#### `src/kalshi_research/research/topic.py`

| Function | Specification |
|----------|--------------|
| `research_topic(topic, ...)` | Research a general topic via Exa. Returns: TopicResearchResult. |

---

## Detection Script

To regenerate this list:

```python
import ast
from pathlib import Path
from collections import defaultdict

results = defaultdict(list)
SKIP = {"__init__", "__aenter__", "__aexit__", "__post_init__", "__str__", "__repr__", "__eq__", "__hash__"}

for py_file in sorted(Path("src").rglob("*.py")):
    try:
        with open(py_file) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_") or node.name in SKIP:
                    continue
                if not ast.get_docstring(node):
                    results[str(py_file)].append(node.name)
    except SyntaxError:
        pass

for filepath, funcs in sorted(results.items(), key=lambda x: -len(x[1])):
    print(f"{filepath}: {', '.join(funcs)}")
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

- Module-level docstrings are already present in all files (100% coverage)
- The 42.97% coverage reported by CodeRabbit includes all functions (including private ones)
- This debt is cosmetic and does not affect functionality
- Prioritize high-traffic API functions first (exa/client.py, execution/executor.py)
- Many "missing" docstrings are for simple properties where the name is self-documenting
