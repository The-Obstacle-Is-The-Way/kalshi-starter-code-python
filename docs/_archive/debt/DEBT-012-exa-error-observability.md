# DEBT-012: Exa Pipeline Error Observability (Missing Trace Context)

**Priority:** P3 (Debuggability / operational ergonomics)
**Status:** ✅ Complete
**Created:** 2026-01-10
**Last Verified:** 2026-01-10
**Resolved:** 2026-01-10

---

## Summary

Several Exa-facing workflows intentionally degrade gracefully on external failures (network issues, quota,
vendor errors). However, many catch-and-continue paths log only `error=str(e)` without `exc_info=True`
(stack trace), which makes real-world debugging slower and can hide the true failure mode (e.g., JSON
schema mismatch vs timeout vs auth).

This is not a functional correctness bug, but it is a “paper cut” that compounds during incidents.

---

## Evidence (SSOT)

Examples of catch-and-continue without stack trace:

- `src/kalshi_research/news/collector.py`: Exa fetch failures log warning without `exc_info=True`
- `src/kalshi_research/research/context.py`: `_collect_sources` logs “Exa search failed” without stack trace
- `src/kalshi_research/research/topic.py`: `_get_answer` / `_get_search` log warnings without stack trace
- `src/kalshi_research/exa/cache.py`: cache read failure logs warning without stack trace

---

## Fix Plan

### 1) Add structured exception context

For these logs, include:
- `exc_info=True`
- operation metadata (query, category, market_ticker) already present in several call sites

### 2) Avoid noisy stack traces by default (optional)

If stack traces are considered too noisy for normal runs, gate them behind:
- `KALSHI_DEBUG=1` or `--verbose`
- or log stack traces at `debug` while keeping a concise warning at `warning`

### 3) Ensure no sensitive data leaks

Confirm logs do not emit API keys or raw auth headers (especially in Exa client failures).

---

## Acceptance Criteria

- [x] Exa-related failures have actionable logs (stack trace available when needed).
- [x] No secrets are logged (validated against sample error paths).
- [x] Tests cover at least one failure path to ensure the log call includes expected fields.
- [x] Quality gates pass.

---

## Implementation Notes (2026-01-10)

- Added `exc_info=True` to Exa-facing catch-and-continue logs:
  - `src/kalshi_research/news/collector.py`
  - `src/kalshi_research/research/context.py`
  - `src/kalshi_research/research/topic.py`
  - `src/kalshi_research/exa/cache.py`
- Updated unit coverage to assert stack-trace capture is enabled:
  - `tests/unit/exa/test_cache.py::test_cache_corrupt_entry_is_evicted`
