# DEBT-005: PriceSnapshot has deprecated `liquidity` dead column

**Priority:** P4 (Low risk / cleanup)
**Status:** ✅ Resolved
**Created:** 2026-01-10
**Resolved:** 2026-01-10

---

## Summary

Kalshi deprecated and removed the `liquidity` field from Market responses (Jan 15, 2026). We correctly:

- stopped using `Market.liquidity` for analysis (liquidity scoring uses orderbook depth + volume/OI)
- added validation to treat negative liquidity values as `None`

However, the database schema still includes a `price_snapshots.liquidity` column, and snapshot writes still
populate it when present. This is not a runtime bug today, but it is **schema drift / dead data** that
increases maintenance surface area and can mislead future development.

This is debt (not a bug) because:

- core logic does not depend on this column
- it does not currently cause incorrect calculations
- removal is a migration/cleanup concern

---

## Evidence (SSOT)

- ORM schema no longer contains `PriceSnapshot.liquidity`:
  - `src/kalshi_research/data/models.py` → `class PriceSnapshot` (column removed)
- Snapshot persistence no longer writes `liquidity`:
  - `src/kalshi_research/data/fetcher.py` → `_api_market_to_snapshot(...)` (no liquidity field)
- API model treats negative values as None and logs a warning:
  - `src/kalshi_research/api/models/market.py` → `handle_deprecated_liquidity()`
- Vendor SSOT notes deprecation/removal:
  - `docs/_vendor-docs/kalshi-api-reference.md` (liquidity removal notes)
- Alembic migration drops the column:
  - `alembic/versions/9e54540e9c31_drop_price_snapshots_liquidity.py`

---

## Impact

- Mild DB bloat (mostly null/garbage values)
- Cognitive overhead / risk of misuse (someone may incorrectly assume it’s meaningful)
- Future migration surface area (schema modernization already on the roadmap)

---

## Clean Fix Specification

### Goal

Remove dead `liquidity` data from snapshots so storage matches current semantics.

### Implemented Steps

1. Alembic migration (implemented):
   - Drop `price_snapshots.liquidity` column.
2. Snapshot materialization (implemented):
   - Remove writing `liquidity` in `_api_market_to_snapshot()`.
3. Validate invariants (confirmed):
   - Liquidity analysis remains based on orderbook depth + volume/open-interest (no dependency on snapshots).

### Backward Compatibility Options

Pick one explicitly:

- ✅ **Hard remove:** drop column + stop writing it.

---

## Acceptance Criteria

- [x] No code reads `PriceSnapshot.liquidity`.
- [x] Fetcher no longer writes `liquidity` to snapshots.
- [x] DB schema no longer contains `price_snapshots.liquidity` (after migration).
- [x] Tests and docs build remain green.

---

## Related

- Prior work handled `Market.liquidity` deprecation in analysis and validation (BUG-048 / TODO-009).
