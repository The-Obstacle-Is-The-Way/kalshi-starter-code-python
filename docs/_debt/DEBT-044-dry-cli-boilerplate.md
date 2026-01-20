# DEBT-044: DRY — Remove Duplicated CLI Boilerplate

## Status

- **Severity:** HIGH
- **Effort:** M (1–2 days)
- **Blocking:** Yes (duplication guarantees future divergence bugs)
- **Target Date:** 2026-02-02
- **Status:** Active

## Problem

The CLI repeats the same patterns dozens of times:

1. **Async wrapper boilerplate** (`asyncio.run(...)`) — 58 copies
2. **Kalshi API error handling** (`except KalshiAPIError ... Exit(1)`) — 28 copies
3. **DB session plumbing** (`DatabaseManager(...)` + session creation) — 11 copies

This violates DRY and creates real risk:
if any behavior (exit codes, logging, messaging) needs to change, we must update it in dozens of places.

## Evidence

Reproduce:

```bash
rg -n "asyncio\\.run\\(" src/kalshi_research/cli | wc -l
rg -n "except KalshiAPIError" src/kalshi_research/cli | wc -l
rg -n "DatabaseManager\\(" src/kalshi_research/cli | wc -l
```

Current counts (2026-01-19 audit, SSOT verified):

- `asyncio.run`: **58**
- `except KalshiAPIError`: **28**
- `DatabaseManager(...)`: **11**

## Solution (Minimal Abstractions, Maximum Removal)

### 1) Centralize async entrypoints

Add a single helper (location: `src/kalshi_research/cli/utils.py`):

- `run_async(fn: Callable[[], Awaitable[T]]) -> T`
- Enforce consistent cancellation/KeyboardInterrupt handling
- Avoid per-command nested `_run()` functions

### 2) Centralize KalshiAPIError handling

Add a single helper:

- `exit_kalshi_api_error(e: KalshiAPIError, *, context: str | None = None) -> NoReturn`
- One canonical formatting for status code + message
- One canonical exit code behavior:
  - `typer.Exit(2)` for “not found” (e.g., 404)
  - `typer.Exit(1)` for all other API errors

### 3) Centralize DB session pattern

Add a helper:

- `open_db_session(db_path: str) -> AsyncContextManager[AsyncSession]` (or similar)
- Enforce one place for `DatabaseManager` lifecycle

### 4) Mechanical migration (no behavior changes)

Refactor CLI modules to call these helpers. Migration should be mechanical and test-backed.

## Definition of Done (Objective)

- [ ] `rg -n \"asyncio\\.run\\(\" src/kalshi_research/cli` returns **0** (or a single occurrence inside the shared helper only)
- [ ] `rg -n \"except KalshiAPIError\" src/kalshi_research/cli` returns **0**
- [ ] `rg -n \"DatabaseManager\\(\" src/kalshi_research/cli` returns **≤ 1** (single helper location)
- [ ] No behavior regressions: `uv run pytest`
- [ ] All quality gates: `uv run pre-commit run --all-files`

## Acceptance Criteria (Phased)

- [ ] Phase A: Add `run_async()` helper and migrate at least one CLI module as a template
- [ ] Phase B: Migrate all CLI modules off direct `asyncio.run()`
- [ ] Phase C: Add `exit_kalshi_api_error()` helper and migrate at least one CLI module as a template
- [ ] Phase D: Migrate all CLI modules off duplicated `except KalshiAPIError` blocks
- [ ] Phase E: Add DB session helper and migrate all CLI DB session setup

**Note (2026-01-19):** This work was implemented on `ralph-wiggum-loop` branch but LOST when that branch was deleted due to conflicts with SPEC-043. Must be redone from scratch.
