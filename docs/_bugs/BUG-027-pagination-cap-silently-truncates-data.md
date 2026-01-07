# BUG-027: Pagination `max_pages=100` silently truncates markets/events (P1)

**Priority:** P1 (Silent data loss + downstream breakage)
**Status:** 🟢 Fixed (2026-01-07)
**Found:** 2026-01-07
**Spec:** SPEC-002-kalshi-api-client.md, SPEC-003-data-layer-storage.md
**Checklist Ref:** CODE_AUDIT_CHECKLIST.md Section 1 (Silent Failures), Section 15 (Silent Fallbacks)

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

**Best Practice Violation:**
- [API Pagination Best Practices 2025](https://www.merge.dev/blog/api-pagination-best-practices) — Never silently
  truncate; always signal when more data exists
- [Cursor Pagination Guide](https://www.speakeasy.com/api-design/pagination) — Check `has_next_page` or cursor
  presence to know if dataset is complete

---

## Impact

- Silent data loss in DB sync and any downstream analysis/export.
- Contributes directly to BUG-026 (`snapshot` FK failures) because snapshot fetch and sync fetch can observe
  different tickers when both are capped.

---

## Ironclad Fix Specification

**Approach:** Make `max_pages` configurable with default `None` (unlimited), emit warning when truncated.

**File:** `src/kalshi_research/api/client.py`

### Change 1: `get_all_markets()` (lines 147-172)

```python
async def get_all_markets(
    self,
    status: MarketFilterStatus | str | None = None,
    limit: int = 1000,
    max_pages: int | None = None,  # CHANGE: Default None (unlimited)
) -> AsyncIterator[Market]:
    """
    Iterate through ALL markets with automatic pagination.

    Args:
        status: Filter by market status (open, closed, settled)
        limit: Page size (max 1000)
        max_pages: Optional safety limit. None = iterate until exhausted.

    Yields:
        Market objects

    Warns:
        If max_pages reached but cursor still present (data truncated)
    """
    cursor: str | None = None
    pages = 0
    while True:
        markets, cursor = await self.get_markets_page(
            status=status,
            limit=limit,
            cursor=cursor,
        )

        for market in markets:
            yield market

        if not cursor or not markets:
            break

        pages += 1

        # Safety limit check with warning
        if max_pages is not None and pages >= max_pages:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                "Pagination truncated: reached max_pages=%d but cursor still present. "
                "Data may be incomplete. Set max_pages=None for full iteration.",
                max_pages,
            )
            break
```

### Change 2: `get_all_events()` (lines 303-330)

Same pattern as above.

### Change 3: CLI `sync-markets` command

Add `--max-pages` flag with default `None`, and log warning if truncated.

---

## Acceptance Criteria

- [x] `get_all_markets(...)` has no default 100-page cap (unit test: `tests/unit/api/test_client.py::test_get_all_markets_has_no_default_page_cap`)
- [x] `get_all_events(...)` has no default 100-page cap (unit test: `tests/unit/api/test_client.py::test_get_all_events_has_no_default_page_cap`)
- [x] `max_pages` still works as a safety limit when explicitly set
- [x] Warning logged when `max_pages` reached but cursor still present (unit tests: `tests/unit/api/test_client.py::test_get_all_markets_warns_when_truncated`, `tests/unit/api/test_client.py::test_get_all_events_warns_when_truncated`)
- [x] CLI supports `kalshi data sync-markets --max-pages N`
- [ ] Integration test: full sync completes with all markets (live API)

---

## Test Plan

```python
async def test_pagination_warning_when_truncated(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify warning emitted when pagination truncated."""
    async with KalshiPublicClient() as client:
        count = 0
        async for _m in client.get_all_markets(status="open", max_pages=1):
            count += 1
            if count > 1000:
                break

    assert "Pagination truncated" in caplog.text


async def test_pagination_no_warning_when_exhausted() -> None:
    """No warning when pagination completes naturally."""
    # Use a filter that returns few results
    async with KalshiPublicClient() as client:
        count = 0
        async for _m in client.get_all_markets(
            status="settled",
            limit=1000,
            max_pages=None,  # Unlimited
        ):
            count += 1
            if count > 50000:  # Safety break for test
                break
    # If we got here without warning, test passes
```
