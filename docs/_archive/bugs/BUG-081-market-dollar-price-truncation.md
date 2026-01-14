# BUG-081: Market `*_dollars` → cents conversion truncates subpenny prices

**Priority:** P2 (Incorrect pricing; inconsistent with orderbook; can skew P&L + scans)
**Status:** ✅ Fixed
**Found:** 2026-01-14
**Verified:** 2026-01-14 - Added unit tests
**Fixed:** 2026-01-14
**Affected Code:** `Market.*_cents` in `src/kalshi_research/api/models/market.py`

---

## Summary

Kalshi is migrating price fields to fixed-point dollar strings (`*_dollars`) and has begun the subpenny pricing
migration. Pre-fix, our `Market` model converted these strings to integer cents via truncation
(`int(Decimal(...) * 100)`), which:

- Floors sub-cent values (e.g., `"0.015"` → `1¢`, not `2¢`)
- Produces inconsistent results vs `Orderbook` dollar conversion (which rounds half-up)
- Propagates into scanners, snapshots, and portfolio mark prices (since they use `Market.*_cents`)

---

## Reproduction (pre-fix)

```python
from kalshi_research.api.models.market import Market

market = Market.model_validate(
    {
        "ticker": "TEST",
        "event_ticker": "EVT",
        "title": "Test",
        "subtitle": "",
        "status": "active",
        "result": "",
        "yes_bid_dollars": "0.015",
        "yes_ask_dollars": "0.025",
        "no_bid_dollars": "0.975",
        "no_ask_dollars": "0.985",
        "volume": 0,
        "volume_24h": 0,
        "open_interest": 0,
        "open_time": "2024-01-01T00:00:00Z",
        "close_time": "2025-01-01T00:00:00Z",
        "expiration_time": "2025-01-02T00:00:00Z",
    }
)

# Observed (pre-fix):
assert market.yes_bid_cents == 1
assert market.yes_ask_cents == 2
assert market.no_bid_cents == 97
assert market.no_ask_cents == 98

# Observed (post-fix):
assert market.yes_bid_cents == 2
assert market.yes_ask_cents == 3
assert market.no_bid_cents == 98
assert market.no_ask_cents == 99
```

For comparison, the `Orderbook` dollar conversion already rounds half-up and has unit test coverage
(`tests/unit/api/test_models.py::test_orderbook_dollar_conversion_rounds_half_up`).

---

## Root Cause

`src/kalshi_research/api/models/market.py` uses:

```python
int(Decimal(self.yes_bid_dollars) * 100)
```

This truncates (floors) fractional cents and does not validate range.

---

## Impact

- Inconsistent derived pricing between `Market` and `Orderbook` for the same dollar-denominated quote data.
- Systematic downward bias for subpenny prices across:
  - `Market.midpoint` (since it relies on truncated cents)
  - Snapshot ingestion (`PriceSnapshot` stores the truncated cents)
  - Portfolio mark pricing (uses `Market.midpoint`)

---

## Proposed Fix

1. Create a shared dollars→cents conversion helper that:
   - Parses `FixedPointDollars` strings via `Decimal`
   - Rounds half-up to the nearest cent
   - Rejects invalid and out-of-range values
2. Use this helper in both:
   - `Market.*_cents` computed properties
   - `Orderbook` dollar conversion
3. Add unit tests for `Market` conversion (half-up rounding + input validation).
4. Decide and document our subpenny policy (round-to-cent vs full precision) in DEBT-025.

---

## Implemented Fix

1. Added a shared conversion helper with half-up rounding + range validation:
   - `src/kalshi_research/api/models/pricing.py::fixed_dollars_to_cents`
2. Updated `Market.*_cents` computed properties to use that helper (eliminates truncation + matches orderbook policy).
3. Updated portfolio mark pricing to round half-up for half-cent midpoints:
   - `src/kalshi_research/portfolio/syncer.py::PortfolioSyncer.update_mark_prices`

---

## Verification

- `tests/unit/api/test_models.py::TestMarketModel::test_market_dollar_conversion_rounds_half_up`
- `tests/unit/api/test_models.py::TestMarketModel::test_market_dollar_conversion_rejects_out_of_range_prices`
- `tests/unit/api/test_models.py::TestMarketModel::test_market_dollar_conversion_rejects_invalid_numbers`
- `tests/unit/portfolio/test_syncer.py::test_update_mark_prices_rounds_half_up_for_half_cent_midpoints`

---

## Related

- `docs/_debt/DEBT-025-subpenny-pricing-strategy.md`
