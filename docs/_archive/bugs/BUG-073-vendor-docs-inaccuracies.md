# BUG-073: Vendor Docs Drift vs Production API (Fixed)

**Priority:** P2 (Docs drift can create bad code + false bug reports)
**Status:** ✅ Fixed
**Found:** 2026-01-12
**Fixed:** 2026-01-12
**Method:** Compared `docs/_vendor-docs/kalshi-api-reference.md` against **raw** production fixtures in `tests/fixtures/golden/`

---

## Summary

Some earlier “vendor docs are wrong” conclusions were **false positives** caused by non-raw golden fixtures (model dumps
lost wrapper keys and altered shapes). After re-recording raw fixtures from production (BUG-072), we updated our vendor
doc to match observed reality where it truly drifted.

---

## Verified Drift (Corrected in Vendor Docs)

### 1) `GET /markets/{ticker}/orderbook`: empty-side behavior

**SSOT (prod fixture):** `tests/fixtures/golden/orderbook_response.json`

- Response includes `orderbook` wrapper: `response.orderbook`
- When empty, sides may be `null` (observed)

**Fix:** Updated `docs/_vendor-docs/kalshi-api-reference.md` to say empty sides may be `null` or omitted.

### 2) `GET /portfolio/positions`: `last_updated_ts` type

**SSOT (prod fixture):** `tests/fixtures/golden/portfolio_positions_response.json`

- `response.market_positions[0].last_updated_ts` is an RFC3339 string (observed), not a Unix int

**Fix:** Updated the positions example in `docs/_vendor-docs/kalshi-api-reference.md` to show an RFC3339 string.

### 3) `GET /portfolio/balance`: missing response keys in docs

**SSOT (prod fixture):** `tests/fixtures/golden/portfolio_balance_response.json`

- Response keys: `balance`, `portfolio_value`, `updated_ts`

**Fix:** Added a `GET /portfolio/balance` response keys section (including `updated_ts`) to `docs/_vendor-docs/kalshi-api-reference.md`.

### 4) `GET /portfolio/fills`: undocumented fields

**SSOT (prod fixture):** `tests/fixtures/golden/portfolio_fills_response.json`

Observed fields per fill include:
- `ts` (Unix seconds)
- `market_ticker` (legacy duplicate of `ticker`)
- `price` (decimal price representation)

**Fix:** Added these fields to the fills response table in `docs/_vendor-docs/kalshi-api-reference.md`.

---

## False Positives Removed

### Orderbook wrapper key

**SSOT:** `tests/fixtures/golden/orderbook_response.json` includes top-level `orderbook`.

Prior claims of “no wrapper key” came from recording processed model dumps instead of raw API JSON.

---

## Related

- **BUG-072**: API SSOT Findings (fixed raw fixtures + model alignment)
