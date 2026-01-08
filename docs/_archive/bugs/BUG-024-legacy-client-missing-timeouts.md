# BUG-024: Legacy `requests` Client Missing Timeouts + Incorrect 2xx Check (P2)

**Priority:** P2 (High - reliability)
**Status:** ✅ Fixed
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Spec:** SPEC-002-kalshi-api-client.md

---

## Summary

The legacy `KalshiHttpClient` (starter-code compatibility layer) made `requests` calls without timeouts, risking indefinite hangs. It also used an incorrect success-range check (`range(200, 299)`), excluding status `299`.

---

## Root Cause

- Missing `timeout=` arguments on `requests.get/post/delete`.
- Off-by-one 2xx range check (`range(200, 299)` yields 200–298).

---

## Fix Applied

- `src/kalshi_research/clients.py`
  - Added `timeout_seconds: float = 10.0` to `KalshiHttpClient` and passed it to all HTTP calls.
  - Updated success check to `200 <= status_code < 300`.

---

## Regression Tests

- Covered by existing unit tests in `tests/unit/test_clients.py` (HTTP methods + error handling).
