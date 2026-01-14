# DEBT-027: Private Function Docstrings

**Priority:** P4 (Cosmetic/Quality)
**Status:** ✅ Resolved
**Found:** 2026-01-14
**Fixed:** 2026-01-14
**Source:** Post-DEBT-026 audit (important private functions)

---

## Summary

Resolved by adding docstrings to 19 important private helpers (prefixed with `_`) that were
intentionally outside the DEBT-026 scope (public callables only). This improves maintainability
and reduces time-to-comprehension for maintainers and AI agents.

---

## Impact

- **Severity:** Low - Does not affect functionality
- **User Impact:** None (private implementation details)
- **Maintainability:** Harder to understand internal logic without reading full implementations

---

## Functions Missing Docstrings (Fixed)

### High Priority: Core Infrastructure

#### `src/kalshi_research/exa/client.py`

| Function | Purpose (inferred from code) |
|----------|------------------------------|
| `ExaClient._request(method, path, ...)` | Core HTTP request method with retry logic, rate limiting, and error handling |
| `ExaClient._parse_retry_after(response)` | Parse `Retry-After` header from rate-limited responses |

#### `src/kalshi_research/execution/executor.py`

| Function | Purpose (inferred from code) |
|----------|------------------------------|
| `TradeExecutor._run_common_checks(count, yes_price_cents)` | Validate basic order constraints (price bounds, count, risk estimate) |
| `TradeExecutor._run_live_checks(ticker, side, action, ...)` | Enforce live-trading guardrails (kill switch, production gating, daily limits, confirmation) |

### Medium Priority: CLI Helpers

#### `src/kalshi_research/cli/research.py`

| Function | Purpose (inferred from code) |
|----------|------------------------------|
| `_fetch_market(ticker)` | Fetch a market from the Kalshi public API and exit with a CLI-friendly error on failure |
| `_run_deep_research(topic, model, wait, ...)` | Create a paid Exa research task and (optionally) wait/poll for completion |
| `_run_market_context_research(market, max_news, max_papers, days)` | Run MarketContextResearcher (Exa + cache) for a given market |
| `_run_topic_research(topic, include_answer)` | Run topic research via TopicResearcher |

#### `src/kalshi_research/cli/scan.py`

| Function | Purpose (inferred from code) |
|----------|------------------------------|
| `_build_new_markets_results(candidates, categories, limit, now)` | Build table rows for the new-markets report (including category filtering + unpriced count) |
| `_fetch_exchange_status(client)` | Fetch and validate exchange status response, returning `None` on non-fatal errors |
| `_parse_category_filter(category)` | Parse and normalize a comma-separated category filter string |
| `_validate_new_markets_args(hours, limit)` | Validate numeric args for the new-markets command and exit on invalid values |

#### `src/kalshi_research/cli/news.py`

| Function | Purpose (inferred from code) |
|----------|------------------------------|
| `_fetch_tracking_targets(ticker, event)` | Resolve a market/event ticker to the corresponding API objects (and a display title) |
| `_parse_search_queries(queries, title)` | Parse a comma-separated `--queries` override or fall back to title-based defaults |

#### `src/kalshi_research/cli/alerts.py`

| Function | Purpose (inferred from code) |
|----------|------------------------------|
| `_run_alert_monitor_loop(monitor, interval, once, max_pages)` | Monitor alert conditions in a loop (or once) and exit cleanly on Ctrl-C |

#### `src/kalshi_research/cli/data.py`

| Function | Purpose (inferred from code) |
|----------|------------------------------|
| `_validate_migrations_on_temp_db(alembic_ini, db_path)` | Dry-run Alembic migrations against a temporary copy of the database |

#### `src/kalshi_research/cli/market.py`

| Function | Purpose (inferred from code) |
|----------|------------------------------|
| `_fetch_markets_for_market_list_from_events(status_filter, include_category_lower, ...)` | Fetch markets via `/events` with nested markets, applying CLI filters and a hard limit |

#### `src/kalshi_research/cli/portfolio.py`

| Function | Purpose (inferred from code) |
|----------|------------------------------|
| `_validate_environment_override(environment)` | Validate an `--env` override and normalize it to `demo`/`prod` |

### Low Priority: Internal Utilities

#### `src/kalshi_research/research/thesis.py`

| Function | Purpose (inferred from code) |
|----------|------------------------------|
| `Thesis._parse_datetime(value)` | Parse an ISO-8601 datetime string (or return `None` for invalid inputs) |

---

## Detection Script

To regenerate this list:

```python
import ast
from collections import defaultdict
from pathlib import Path

IMPORTANT_PREFIXES = (
    "_request", "_auth", "_fetch", "_build", "_parse",
    "_validate", "_run", "_execute", "_create", "_send"
)

results = defaultdict(list)

for py_file in sorted(Path("src").rglob("*.py")):
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except SyntaxError:
        continue

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith(IMPORTANT_PREFIXES) and not ast.get_docstring(node):
                results[str(py_file)].append(node.name)

        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name.startswith(IMPORTANT_PREFIXES) and not ast.get_docstring(item):
                        results[str(py_file)].append(node.name + "." + item.name)

for filepath, funcs in sorted(results.items(), key=lambda x: (-len(x[1]), x[0])):
    print(filepath + ": " + ", ".join(sorted(funcs)))
```

---

## Docstring Format

Follow Google-style docstrings. For private helpers, a one-liner is often sufficient:

```python
def _fetch_market(ticker: str) -> KalshiMarket | None:
    """Fetch a market from DB cache, falling back to API if not found."""
    ...
```

For complex internal logic, include Args/Returns/Raises:

```python
def _run_common_checks(self, *, count: int, yes_price_cents: int) -> tuple[float, list[str]]:
    """Validate basic order constraints before execution.

    Args:
        count: Number of contracts to trade.
        yes_price_cents: YES price in cents (1-99).

    Returns:
        Tuple of (estimated_risk_usd, list of failure reasons).
    """
    ...
```

---

## Notes

- These functions are private implementation details (prefixed with `_`)
- The "Purpose (inferred from code)" column contains best-effort descriptions that should be verified against actual implementation before adding docstrings
- Priority is P4 because this is cosmetic and doesn't affect functionality

---

## Resolution Notes

- Added docstrings to all 19 functions listed above.
- Confirmed via the detection script in this document: `All important private functions have docstrings`.
- Quality gates passed: `uv run pre-commit run --all-files`, `uv run pytest -q`.
