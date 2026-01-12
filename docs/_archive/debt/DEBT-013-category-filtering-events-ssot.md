# DEBT-013: Category Filtering Must Use `/events` (Not `/markets`) as SSOT

**Priority:** Medium (Research UX correctness)
**Status:** ✅ Resolved
**Found:** 2026-01-11
**Resolved:** 2026-01-11

---

## Summary

`kalshi market list --category ...` and `kalshi scan opportunities --category ...` were effectively broken in
production-like conditions because they:

1. Fetched markets from `GET /markets` (which is heavily dominated by Sports multivariate markets early in
   pagination).
2. Classified “category” using **event_ticker prefix heuristics** (incomplete + not aligned with Kalshi’s real
   categories).

This produced false negatives like “No markets found” for legitimate categories such as Politics or
Science-and-Technology.

---

## Root Cause (First Principles)

- `GET /markets` does **not** support server-side category filtering.
- Market objects no longer include a `category` field (removed Jan 8, 2026).
- Kalshi’s **authoritative** category lives on `EventData.category` (and the OpenAPI spec notes this is
  deprecated in favor of *series-level* category, but it is still populated today).
- `GET /events` supports `with_nested_markets=true`, returning **Event + Markets** in one call, and it also
  excludes multivariate events (which are the main source of “sports parlay spam” in `/markets` pagination).

So: **Category filtering must be driven from `/events`, not from `/markets` + heuristics.**

---

## Fix (Implemented)

### Behavior

- Category filters now use `GET /events?with_nested_markets=true` and match against `Event.category`
  (case-insensitive, with CLI aliases like `ai → Science and Technology`).
- This path avoids “first N pages are all Sports MVE” failure modes and makes `--category` actually work.

### Code Changes

- `src/kalshi_research/api/models/event.py`: Add optional `markets` field to parse nested markets.
- `src/kalshi_research/api/client.py`: Add `with_nested_markets` flag to `get_events_page()`, `get_events()`,
  and `get_all_events()`.
- `src/kalshi_research/cli/market.py`: When `--category/--exclude-category/--event-prefix` are used (and the
  status supports events), fetch via `get_all_events(..., with_nested_markets=True)` and filter on
  `Event.category`.
- `src/kalshi_research/cli/scan.py`: When `--category/--no-sports/--event-prefix` are used, fetch via events
  + nested markets instead of scanning `/markets` pages.

### Tests

- `tests/unit/cli/test_market.py`: Updated category/exclude/prefix tests to mock `get_all_events()`.
- `tests/unit/cli/test_scan.py`: Updated `--category` and `--no-sports` tests to mock `get_all_events()`.

---

## Residual Risk / Future Work

- OpenAPI spec warns `EventData.category` is deprecated in favor of **Series.category**. If Kalshi removes
  `Event.category` in the future, migrate to `/series` category as SSOT:
  - Fetch series list / series details, build `series_ticker → category`.
  - Map events via `event.series_ticker`.
  - Keep the same CLI contract (`--category`), only swap the backing data source.
