# BUG-016: `kalshi data snapshot` Fails Without Prior Init (P1)

**Priority:** P1 (High - common workflow breaks on fresh DB)
**Status:** ✅ Fixed
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Spec:** SPEC-003-data-layer-storage.md, SPEC-010-cli-completeness.md

---

## Summary

`kalshi data snapshot` previously attempted to insert snapshots without ensuring tables existed, which could fail on a fresh database file.

---

## Root Cause

Unlike `kalshi data init` and `kalshi data sync-markets`, the snapshot command did not call `DatabaseManager.create_tables()` before writing.

---

## Fix Applied

`kalshi data snapshot` now calls `DatabaseManager.create_tables()` before taking snapshots.

---

## Regression Tests Added

- `tests/integration/cli/test_cli_commands.py`
- `tests/e2e/test_data_pipeline.py`
