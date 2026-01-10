# DEBT-006: Price snapshot inserts flush/refresh per row (defeats batching)

**Priority:** P3 (Performance / scale)
**Status:** ✅ Resolved
**Created:** 2026-01-10
**Resolved:** 2026-01-10

---

## Summary

`DataFetcher.take_snapshot()` intended to batch DB writes (explicit `session.flush()` every 100 rows), but it used
`BaseRepository.add()`, which performed `flush()` and `refresh()` **for every snapshot**. This:

- defeats batching,
- adds an extra SELECT per row (`refresh`),
- makes full-market snapshots materially slower as market count grows.

This is technical debt (not correctness) because results were still correct, but performance and code intent were
misaligned.

---

## Evidence (SSOT)

Prior to the fix:

- `src/kalshi_research/data/fetcher.py` called `await price_repo.add(snapshot)` inside the snapshot loop.
- `src/kalshi_research/data/repositories/base.py` implemented `add()` as:
  - `session.add(...)`
  - `await session.flush()`
  - `await session.refresh(entity)`
- `src/kalshi_research/data/fetcher.py` also contained an explicit batch flush (`if count % 100 == 0:
  await session.flush()`), implying intended batching that wasn’t actually happening.

---

## Root Cause

The repository abstraction optimized for “CRUD correctness” (flush+refresh to ensure PK/defaults are available),
but the data pipeline hot path (price snapshots) is bulk-ingest and does not need refresh.

This is the classic mismatch:

- generic repo default behavior
- used in a high-volume ingestion loop

---

## Ironclad Fix

1. Make repository insertion controllable and cheaper:
   - `BaseRepository.add(..., flush: bool = True)` now supports `flush=False`.
   - Remove `refresh()` from `add()` and `add_many()`; PKs are available on flush for SQLite and we do not rely
     on server-side defaults in this repo.
2. Apply it in the hot path:
   - `DataFetcher.take_snapshot()` calls `await price_repo.add(snapshot, flush=False)` and retains explicit
     batch `session.flush()` calls.

---

## Acceptance Criteria

- [x] Snapshot ingestion no longer flushes per row.
- [x] Snapshot ingestion no longer refreshes per row.
- [x] Existing repository consumers retain the default `flush=True` behavior.
- [x] Full quality gates pass (`uv run pre-commit run --all-files`).

---

## Files Changed

- `src/kalshi_research/data/repositories/base.py`
- `src/kalshi_research/data/fetcher.py`
