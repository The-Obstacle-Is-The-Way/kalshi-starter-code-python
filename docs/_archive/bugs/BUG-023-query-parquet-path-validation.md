# BUG-023: `query_parquet()` Missing Path Validation (DuckDB SQL Injection Surface) (P2)

**Priority:** P2 (High - security hardening)
**Status:** ✅ Fixed
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Spec:** SPEC-003-data-layer-storage.md

---

## Summary

`query_parquet()` built DuckDB SQL strings using a user-provided directory path without validating for quote/statement characters. This created a SQL-injection surface (local execution context, but still unsafe-by-default).

---

## Root Cause

`query_parquet()` interpolated filesystem paths into SQL (e.g., `CREATE VIEW ... FROM '...path...'`) without validating characters like `'`, `"`, `;`, or `--`.

---

## Fix Applied

- `src/kalshi_research/data/export.py`
  - Added the same path validation used by exporters to `query_parquet()`.

---

## Regression Tests Added

- `tests/unit/data/test_export.py::test_query_parquet_rejects_invalid_path`
