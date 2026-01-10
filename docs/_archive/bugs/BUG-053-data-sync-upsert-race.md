# BUG-053: Data sync is not concurrency-safe (IntegrityError on upsert)

**Priority**: P3 (Data pipeline reliability / scaling risk)
**Status**: Fixed
**Created**: 2026-01-10
**Resolved**: 2026-01-10

---

## Summary

Before the fix, running **two writers** against the same SQLite database (or the same table rows) could
raise `sqlalchemy.exc.IntegrityError` (UNIQUE constraint) and abort the current transaction.

This is not just a “multi-process someday” concern:

- Before the fix, `kalshi data collect` could run overlapping DB writes in-process: it started the
  scheduler (which ran interval tasks immediately) while also performing an initial `full_sync`.
- Before the fix, multi-process overlap (two CLIs / cron overlap) also triggered this race.

The underlying problem is systemic: repository “upsert” methods are implemented as
`get(pk)` → `add(entity)`, and `BaseRepository.add()` flushes immediately, so a concurrent insert between
`get()` and `flush()` will raise.

---

## Why This Matters

This can cause:

- missed snapshot/sync cycles (data holes)
- flaky “continuous collection” runs (`kalshi data collect`) with intermittent errors in logs
- non-deterministic failures that are hard to reproduce/debug
- future scaling risk if we add parallel workers

Because we use `session.begin()` for safety, one integrity failure can roll back the entire batch
(losing the work done in that transaction).

---

## Reproduction

### Repro A (deterministic): concurrent inserts on same PK

This is the minimal, deterministic shape of the bug:

```python
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy.exc import IntegrityError

from kalshi_research.data.database import DatabaseManager
from kalshi_research.data.models import Event


async def insert_event(db: DatabaseManager) -> None:
    async with db.session_factory() as session:
        async with session.begin():
            session.add(Event(ticker="EVT", series_ticker="SER", title="TITLE"))
            await session.flush()


async def main() -> None:
    with TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        async with DatabaseManager(db_path) as db:
            await db.create_tables()
            results = await asyncio.gather(insert_event(db), insert_event(db), return_exceptions=True)
            assert any(isinstance(r, IntegrityError) for r in results)


asyncio.run(main())
```

### Repro B (realistic): overlapping cron runs / two CLIs

This reproduces the bug on the pre-fix version.

1. Configure two cron jobs that both run market sync with the same `--db` path on a tight schedule, e.g.
   every minute.
2. Ensure the schedule overlaps (make one start slightly later than the other).
3. Observe intermittent failures:
   - `sqlalchemy.exc.IntegrityError: UNIQUE constraint failed: ...`
   - potential follow-on errors due to transaction rollback.

Or, in two different terminals:

```bash
uv run kalshi data sync-markets --db data/kalshi.db --status open
```

### Repro C (in-process): `kalshi data collect` overlap on startup

Before the fix, `kalshi data collect` started the scheduler, then ran `full_sync`. The scheduler
immediately ran both `market_sync` and `price_snapshot` tasks (by design) while `full_sync` was running.
This created multiple writers in one process.

This overlap exists unless we serialize DB writes or delay scheduled tasks until after the initial sync.

---

## Root Cause (First Principles)

### 1) “Upsert” is not atomic

Before the fix, repository `upsert()` methods were implemented as:

- `existing = await self.get(pk)`
- if existing: update + flush
- else: `await self.add(entity)`

This is not safe if another writer can insert the same primary key between `get()` and `add()`.

### 2) `BaseRepository.add()` flushes immediately

`BaseRepository.add()` does (and did during the bug):

- `session.add(entity)`
- `await session.flush()`

So the unique constraint check triggers immediately during `add()`, not at commit time.

### 3) DataFetcher does “check then add” for FK robustness (multiple places)

Before the fix:

- `DataFetcher.sync_markets()` created placeholder `Event` rows via `get()` then `add()`.
- `DataFetcher.sync_settlements()` did the same for FK robustness.
- `DataFetcher.take_snapshot()` did `market_repo.get()` then `event_repo.get()` then `event_repo.add()`,
  then `market_repo.upsert()`.

All of these are safe only if there is exactly one writer.

### 4) The scheduler can create overlapping writers in one process

`DataScheduler.schedule_interval()` runs tasks concurrently and triggers an immediate run at startup.
Before the fix, `kalshi data collect` started the scheduler before the initial `full_sync`, so scheduled
tasks could overlap with `full_sync` and with each other.

---

## Impact

**Single process (pre-fix):** `kalshi data collect` could run overlapping writers; failures were
timing-dependent.

**Multi-process (pre-fix / cron overlap):** intermittent failures with rollback:

- Market/event/settlement sync may abort mid-run and leave the DB stale.
- Batch jobs become unreliable and require manual reruns.
- Debugging becomes difficult because failures are timing-dependent.

---

## Ironclad Fix Specification

### Goal

Make database writes **idempotent** and **safe under concurrent writers**, without requiring higher-level
locks as the only mitigation.

### Fix 0 (immediate): prevent in-process overlapping writers

Make it impossible for `kalshi data collect` to run DB writers concurrently by design:

- Do the initial `full_sync` **before** starting scheduled interval tasks, OR
- Change the scheduler to support “start after delay / do not run immediately”, OR
- Add a single shared async lock around scheduled task execution (serialize tasks), OR
- Add a single shared async lock inside `DataFetcher` to serialize write methods when reused by a scheduler.

This addresses the “one process, multiple tasks” failure mode immediately.

### Fix 1 (robust): real DB-level upsert (SQLite dialect)

Implement DB-level upserts for core tables using SQLite’s `ON CONFLICT` behavior (via SQLAlchemy dialect):

- Events: `ON CONFLICT(ticker) DO NOTHING` (placeholder is fine; we mainly need FK satisfaction)
- Markets: `ON CONFLICT(ticker) DO UPDATE SET ...` (update metadata)
- Settlements: `ON CONFLICT(ticker) DO UPDATE SET ...` (update settlement details)

Implementation approach:

- Add “insert-or-ignore / upsert” helpers in repositories (or a shared helper for SQLite).
- Stop doing `get()` checks for existence in hot write paths.
- Ensure `sync_markets`/`sync_settlements`/`take_snapshot` use those helpers.

### Option 2 (acceptable): single-writer lock (process-level)

If we explicitly decide “this codebase is single-writer”, we can:

- add a file lock at CLI entrypoints that write to DB (data sync, snapshot, settlements)
- detect lock contention and exit cleanly with a message

This prevents concurrency, but does not address the underlying non-atomic upserts.

### Option 3 (not recommended as primary): catch IntegrityError and retry

This is brittle and can cause partial work / repeated flush failures unless carefully scoped.

---

## Acceptance Criteria

- [x] `kalshi data collect` does not start overlapping writers at startup (no concurrent
      market_sync/snapshot/full_sync).
- [x] Two concurrent `kalshi data sync-markets` runs against the same DB do not crash with
      `IntegrityError`.
- [x] Two concurrent `kalshi data sync-settlements` runs against the same DB do not crash with
      `IntegrityError`.
- [x] Upserts are DB-level (atomic) and in-process concurrency is serialized in `data collect`.
- [x] Unit tests cover the concurrency scenario (deterministic reproduction using two concurrent runs).

---

## Resolution

Implemented both a DB-level fix and an orchestration fix:

- DB-level upserts for `events`, `markets`, and `settlements` using SQLite `ON CONFLICT` (atomic).
- Replaced `get()` → `add()` check-then-act patterns in the data fetcher with `insert_ignore`/upsert calls.
- Prevented in-process overlap in `kalshi data collect` by running the initial `full_sync` before starting
  the scheduler, delaying interval tasks (`run_immediately=False`), and serializing scheduled writers with
  a shared async lock.

## Changes Made

- `src/kalshi_research/data/repositories/events.py`: Add DB-level `upsert()` and `insert_ignore()`.
- `src/kalshi_research/data/repositories/markets.py`: Add DB-level `upsert()` and `insert_ignore()`.
- `src/kalshi_research/data/repositories/settlements.py`: Add DB-level `upsert()`.
- `src/kalshi_research/data/fetcher.py`: Replace check-then-add patterns with `insert_ignore`/upsert.
- `src/kalshi_research/data/scheduler.py`: Add `run_immediately` option for interval scheduling.
- `src/kalshi_research/cli/data.py`: Avoid startup overlap and serialize scheduled DB writers.
- `tests/unit/data/test_concurrency.py`: Add regression tests for concurrent `sync_markets` and
  `sync_settlements`.

## Verification

- `uv run pytest -q tests/unit/data/test_concurrency.py`
- `uv run pytest -m "not integration and not slow"`

## Remaining Limitations / Non-Goals

- SQLite remains effectively single-writer. Even with atomic upserts, truly concurrent multi-process write
  workloads can still hit `sqlite3.OperationalError: database is locked` depending on timing and busy
  timeout settings. This bug fix targets UNIQUE/IntegrityError races, not SQLite lock contention.

## Notes / Related Files

- `src/kalshi_research/data/fetcher.py` (market + settlement sync)
- `src/kalshi_research/data/fetcher.py` (`take_snapshot` also does get-then-add)
- `src/kalshi_research/data/repositories/base.py` (`add()` flush semantics)
- `src/kalshi_research/data/repositories/events.py`
- `src/kalshi_research/data/repositories/markets.py`
- `src/kalshi_research/data/repositories/settlements.py`
- `src/kalshi_research/data/scheduler.py` (concurrent scheduled tasks)
- `src/kalshi_research/cli/data.py` (`data collect` orchestrates scheduler + initial full_sync)
