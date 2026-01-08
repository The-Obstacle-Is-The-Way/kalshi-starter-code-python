# BUG-035: Scan/Snapshot Commands Missing `--max-pages` Safety Limit (P3)

**Priority:** P3 (Medium - UX/perf, rate-limit resilience)
**Status:** ✅ Fixed (2026-01-07)
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Checklist Ref:** code-audit-checklist.md Section 15 (Silent Fallbacks)

---

## Summary

Several CLI commands fetch *all* open markets via `get_all_markets()` with no way to set a pagination safety limit. This makes commands appear “hung” during long fetches and increases the chance of rate limiting during exploratory runs.

---

## Root Cause

- `KalshiPublicClient.get_all_markets(max_pages=...)` supports a safety limit and warns when truncation occurs.
- CLI commands did not expose that knob, and `DataFetcher.take_snapshot()`/`full_sync()` could not pass it through.

---

## Fix Applied

- Added `--max-pages` to long-running CLI operations:
  - `kalshi data snapshot --max-pages`
  - `kalshi data collect --max-pages`
  - `kalshi scan opportunities --max-pages`
  - `kalshi scan arbitrage --max-pages`
  - `kalshi scan movers --max-pages`
  - `kalshi alerts monitor --max-pages`
- Added passthrough support in `DataFetcher`:
  - `DataFetcher.take_snapshot(..., max_pages=...)`
  - `DataFetcher.full_sync(max_pages=...)`

---

## Acceptance Criteria

- [x] Long-running CLI fetches can be bounded via `--max-pages`
- [x] When bounded, the underlying client warns if results are truncated
- [x] Unit/integration tests still pass
