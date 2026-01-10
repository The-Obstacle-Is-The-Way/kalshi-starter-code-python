# BUG-054: Portfolio CLI crashes on fresh/empty DB (missing tables)

**Priority**: P3 (CLI robustness / onboarding)
**Status**: Fixed
**Created**: 2026-01-10
**Resolved**: 2026-01-10

---

## Summary

Before the fix, several portfolio CLI commands opened a SQLite session and immediately ran `SELECT`
queries without first ensuring the portfolio tables existed. On a fresh machine (or after deleting/moving
the DB), these commands crashed with `sqlite3.OperationalError: no such table: ...` instead of printing a
helpful message.

This is a bad UX footgun because:

- `kalshi portfolio positions` reads as “view my portfolio”, which should degrade gracefully even if the
  local cache hasn’t been initialized.
- The user may not realize that portfolio commands are backed by the *local database*, which is populated
  by `kalshi portfolio sync`.

---

## Affected Commands (pre-fix behavior)

Before the fix, these commands created `DatabaseManager(db_path)` and queried without calling
`create_tables()`:

- `kalshi portfolio positions`
- `kalshi portfolio pnl`
- `kalshi portfolio history`
- `kalshi portfolio link`
- `kalshi portfolio suggest-links`

All of these can fail if the DB file is missing or tables don’t exist yet.

---

## Reproduction

This reproduces the bug on the pre-fix version.

1. Move or delete the DB file (default `data/kalshi.db`) so it doesn’t exist.
2. Run any of:

```bash
uv run kalshi portfolio positions
uv run kalshi portfolio pnl
uv run kalshi portfolio history
```

3. Observe a traceback from SQLite/SQLAlchemy indicating missing tables, e.g.:

```text
sqlite3.OperationalError: no such table: positions
```

---

## Root Cause (First Principles)

### 1) Portfolio read commands assume the local DB cache has been initialized

Before the fix, unlike `kalshi portfolio sync`, these commands did not call:

```python
await db.create_tables()
```

So the first `SELECT` hits an empty SQLite file with no schema → OperationalError.

### 2) The local DB is a cache, but the CLI doesn’t treat it like one

For cache-backed CLIs, the standard behavior is:

- if cache not initialized → print actionable message (“run X first”)
- do not traceback for expected initial conditions

---

## Impact

Before the fix:

- New users experienced “it’s broken” on first run.
- Users troubleshooting auth/env issues could get irrelevant DB errors.
- Portfolio tooling felt fragile.

---

## Ironclad Fix Specification

### Goal

Portfolio read commands should be safe to run at any time and should provide clear guidance.

### Fix A (simple + robust): ensure schema exists

Before any queries, do:

- `await db.create_tables()`

Pros:

- idempotent and cheap
- removes all “no such table” errors

Cons:

- creates an empty DB file even if the user never intends to use portfolio features

### Fix B (best UX): detect missing tables and instruct user

Behavior:

- If DB file missing or missing required tables:
  - print: “Local portfolio cache not initialized. Run `kalshi portfolio sync` first.”
  - exit 0 (or 1 only if this should be treated as an error in scripts)

Implementation approaches (choose one):

- Check `db_path.exists()` and/or query `sqlite_master` for required tables.
- Catch `sqlalchemy.exc.OperationalError` with “no such table” and translate to user message.

### Fix C (hybrid): create tables for read-only, but also message when empty

Do `create_tables()`, then if no rows:

- `No open positions found` plus a hint:
  - “Tip: run `kalshi portfolio sync` to populate the local cache.”

---

## Resolution

Implemented Fix C:

- Ensure schema exists via `DatabaseManager.create_tables()` for portfolio commands that query the local
  DB cache.
- When the local cache is empty, print a tip to run `kalshi portfolio sync`.

## Changes Made

- `src/kalshi_research/cli/portfolio.py`: Call `create_tables()` for positions/pnl/history/link/suggest-links
  and print a sync tip when the local cache is empty.
- `tests/unit/cli/test_portfolio.py`: Add a regression test for running `portfolio positions` on a fresh DB.

## Verification

- `uv run pytest -q tests/unit/cli/test_portfolio.py::test_portfolio_positions_fresh_db_does_not_crash`
- `uv run pytest -m "not integration and not slow"`

## Acceptance Criteria

- [x] Running `kalshi portfolio positions` on a fresh DB does **not** traceback.
- [x] Running `kalshi portfolio pnl` on a fresh DB does **not** traceback.
- [x] Running `kalshi portfolio history` on a fresh DB does **not** traceback.
- [x] Empty-cache messages are actionable and mention `kalshi portfolio sync`.
- [x] Unit tests cover the fresh DB scenario (one per command group is sufficient).

---

## Notes / Related Files

- `src/kalshi_research/cli/portfolio.py`
- `src/kalshi_research/data/database.py` (`create_tables()` is available and idempotent)
- `src/kalshi_research/portfolio/models.py` (tables that may be missing)
