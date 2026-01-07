# BUG-027: Pagination `max_pages=100` silently truncates markets/events (P1)

**Priority:** P1 (Silent data loss + downstream breakage)
**Status:** 🟡 Open
**Found:** 2026-01-07
**Spec:** SPEC-002-kalshi-api-client.md, SPEC-003-data-layer-storage.md

---

## Summary

The public API iterators (`get_all_markets`, `get_all_events`) hard-cap pagination at `max_pages=100` and stop
silently when the cap is reached, even if the API still has a next cursor.

This can truncate:

- Open markets at 100,000 rows (`100 pages * 1000/page`)
- Events at 20,000 rows (`100 pages * 200/page`)

---

## Evidence / Reproduction

### Markets

The API yields **at least** 101,000 open markets:

```bash
uv run python - <<'PY'
import asyncio
from kalshi_research.api import KalshiPublicClient

async def main() -> None:
    async with KalshiPublicClient() as client:
        count = 0
        async for _m in client.get_all_markets(status="open", limit=1000, max_pages=101):
            count += 1
        print(count)

asyncio.run(main())
PY
```

Observed output: `101000`

### Events

The API yields **at least** 20,200 events:

```bash
uv run python - <<'PY'
import asyncio
from kalshi_research.api import KalshiPublicClient

async def main() -> None:
    async with KalshiPublicClient() as client:
        count = 0
        async for _e in client.get_all_events(limit=200, max_pages=101):
            count += 1
        print(count)

asyncio.run(main())
PY
```

Observed output: `20200`

### CLI symptom

`uv run kalshi data sync-markets --status open` reports exactly `100000` markets and `20000` events, consistent
with the cap, and provides no warning that the sync may be partial.

---

## Root Cause

- `KalshiPublicClient.get_all_markets(..., max_pages=100)` / `get_all_events(..., max_pages=100)` have a hard stop
  condition (`while pages < max_pages`) intended as a safety guard.
- When the loop terminates due to reaching `max_pages`, the iterator ends silently, with no signal to callers that
  the dataset is incomplete.

---

## Impact

- Silent data loss in DB sync and any downstream analysis/export.
- Contributes directly to BUG-026 (`snapshot` FK failures) because snapshot fetch and sync fetch can observe
  different tickers when both are capped.

---

## Proposed Fix

- Remove the fixed cap for production paths, or make it configurable (CLI flags, env var).
- Add detection and explicit signaling:
  - If `pages == max_pages` and `cursor` is still present, raise or print a warning and return a “partial” status.
  - Detect repeated cursors to prevent true infinite loops (instead of arbitrary fixed caps).

---

## Acceptance Criteria

- `get_all_markets(status="open")` can iterate past 100,000 markets without truncation.
- `get_all_events()` can iterate past 20,000 events without truncation.
- `kalshi data sync-markets` warns/errors when pagination truncation occurs.

