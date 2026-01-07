# BUG-013: Database Init Omits Portfolio Tables (P1)

**Priority:** P1 (High - breaks portfolio commands)
**Status:** ✅ Fixed
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Spec:** SPEC-003-data-layer-storage.md, SPEC-011-manual-trading-support.md

---

## Summary

`DatabaseManager.create_tables()` only created tables defined in `src/kalshi_research/data/models.py`, omitting portfolio tables (`positions`, `trades`) defined in `src/kalshi_research/portfolio/models.py`. This could cause `kalshi portfolio ...` commands to fail against a freshly initialized database.

---

## Root Cause

SQLAlchemy only creates tables that are registered on `Base.metadata` at runtime. The portfolio models share the same `Base` but were not imported when `create_all()` ran.

---

## Fix Applied

- Import portfolio models during database initialization so `Base.metadata` includes `positions` and `trades` before `create_all()` runs.
- Import portfolio models in Alembic env so autogenerate has complete metadata.

---

## Regression Tests Added

- `tests/integration/data/test_database_manager_integration.py`
- `tests/integration/data/test_alembic_migrations.py`
