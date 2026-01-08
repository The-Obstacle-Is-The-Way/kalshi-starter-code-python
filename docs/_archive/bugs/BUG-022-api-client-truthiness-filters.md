# BUG-022: API Client Drops 0-Valued Params + Uncapped Fills Limit (P2)

**Priority:** P2 (High - correctness / edge cases)
**Status:** ✅ Fixed
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Spec:** SPEC-002-kalshi-api-client.md

---

## Summary

Several optional integer query parameters were gated by truthiness (`if min_ts:`), causing valid `0` values to be omitted from requests. Additionally, the authenticated `/portfolio/fills` limit was not capped defensively.

---

## Root Cause

- `0` is falsy in Python; `if min_ts:` conflates “missing” with “0”.
- Missing defensive cap on `limit` for endpoints with documented max page sizes.

---

## Fix Applied

- `src/kalshi_research/api/client.py`
  - Switched to explicit `is not None` checks for `min_ts`, `max_ts`, `start_ts`, `end_ts`.
  - Capped `get_fills(limit=...)` to `min(limit, 200)`.

---

## Regression Tests Added

- `tests/unit/api/test_client.py` (0-valued timestamps preserved)
- `tests/unit/api/test_client_extended.py` (fills `limit` cap + 0 timestamps)
