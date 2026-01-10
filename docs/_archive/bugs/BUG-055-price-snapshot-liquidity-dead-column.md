# BUG-055: PriceSnapshot has deprecated `liquidity` dead column (reclassified as debt)

**Priority:** P4 (Low risk / tech debt)
**Status:** ✅ Closed (Not a bug; tracked as DEBT-005)
**Created:** 2026-01-10
**Resolved:** 2026-01-10

---

## Summary

This was initially filed as a bug, but it is **technical debt** (dead data / schema drift), not a runtime bug.

Tracking:

- Resolved debt item: `docs/_archive/debt/DEBT-005-price-snapshot-liquidity-dead-column.md`

---

## Reproduction / Evidence

- Schema (at time of filing): `PriceSnapshot.liquidity` existed in ORM model.
- Fetch path (at time of filing): snapshots were populated with `api_market.liquidity`.
- API model validates negative values and converts to None:
  - `src/kalshi_research/api/models/market.py` → `handle_deprecated_liquidity()`

---

## Root Cause

This is a “safe deprecation” but not a “schema removal”:

- App logic no longer depends on `liquidity`.
- Storage layer still contains and writes the column.

---

## Impact

- No known runtime failures.
- Increased risk of future misuse and incorrect analysis if someone accidentally uses this column.
- Minor DB bloat and extra cognitive load.

---

## Ironclad Fix Specification

### Goal

Remove dead `liquidity` data from snapshots so the schema matches current semantics.

### Proposed Steps

1. Alembic migration:
   - Drop `price_snapshots.liquidity` column.
2. Update snapshot materialization:
   - Remove setting `liquidity` in `_api_market_to_snapshot()`.
3. Verify analysis remains unchanged:
   - Liquidity analysis should continue to use orderbook depth + volume/open-interest only.

### Backward Compatibility

If we want to preserve historical provenance, consider:

- leaving the column in old DBs but never writing it (no migration), OR
- migrating it into a “legacy” table, OR
- keeping it until a larger DB migration window (e.g., TODO-009 / schema modernization).

---

## Acceptance Criteria

- [x] No code reads `PriceSnapshot.liquidity` (already true; re-verify).
- [x] Fetcher no longer writes `liquidity` to snapshots.
- [x] DB schema no longer contains `price_snapshots.liquidity` (after migration).
- [x] Tests and mkdocs build remain green.

---

## Notes / Related Files

- `src/kalshi_research/data/models.py`
- `src/kalshi_research/data/fetcher.py`
- `src/kalshi_research/api/models/market.py`
- `docs/_vendor-docs/kalshi-api-reference.md` (liquidity deprecation notes)
