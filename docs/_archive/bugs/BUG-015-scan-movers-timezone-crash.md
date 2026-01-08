# BUG-015: `kalshi scan movers` Timezone Comparison Crash (P1)

**Priority:** P1 (High - CLI command crashes on real SQLite data)
**Status:** ✅ Fixed
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Spec:** SPEC-010-cli-completeness.md, SPEC-003-data-layer-storage.md

---

## Summary

`kalshi scan movers` raised:

```
TypeError: can't compare offset-naive and offset-aware datetimes
```

when filtering historical snapshots against a UTC cutoff.

---

## Root Cause

SQLite does not preserve timezone offsets. SQLAlchemy can return `snapshot_time` as a naive `datetime`, while the CLI used timezone-aware `datetime.now(UTC)` for the cutoff.

---

## Fix Applied

Normalized snapshot timestamps during in-Python filtering:

- Treat naive datetimes as UTC
- Convert aware datetimes to UTC before comparison

---

## Regression Tests Added

- `tests/integration/cli/test_cli_commands.py`
