# BUG-033: Market Model API Schema Mismatch (P0)

**Priority:** P0 (Critical - breaks public market ingestion)
**Status:** ✅ Fixed (2026-01-07)
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Spec:** SPEC-002-kalshi-api-client.md
**Checklist Ref:** CODE_AUDIT_CHECKLIST.md Section 11 (Incomplete Implementations)

---

## Summary

The `Market` Pydantic model rejected legitimate live API values, causing `ValidationError` mid-pagination and breaking any command that iterates through market lists.

---

## Root Cause

Two fields in `src/kalshi_research/api/models/market.py` were too restrictive:

- `MarketStatus` enum did not include `inactive`
- `liquidity` was constrained to `ge=0`, but live API may return negative values

---

## Impact

- Public scanners and data collection could crash when an `inactive` market appears in `/markets` pagination.

Confirmed via live API (2026-01-07): `KXEPLGOAL-26JAN07BURMUN-BUROSONNE22-1` returned `status="inactive"`.

---

## Fix Applied

- Added `MarketStatus.INACTIVE = "inactive"`
- Removed the non-negative constraint on `Market.liquidity`

---

## Acceptance Criteria

- [x] `KalshiPublicClient.get_all_markets()` no longer raises validation errors on `status="inactive"`
- [x] Market model accepts negative `liquidity`
- [x] Unit tests cover both cases

---

## Regression Tests Added

- `tests/unit/api/test_models.py::TestMarketModel.test_market_status_enum_parsing` (includes `inactive`)
- `tests/unit/api/test_models.py::TestMarketModel.test_market_allows_negative_liquidity`
