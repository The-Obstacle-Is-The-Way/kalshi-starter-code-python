# BUG-012: Missing MarketStatus Enum Value (P1)

**Priority:** P1 (High - Blocks data sync)
**Status:** ✅ Fixed
**Found:** 2026-01-07
**Fixed:** 2026-01-07

---

## Summary

The `MarketStatus` enum was missing the `initialized` value, causing Pydantic validation to fail when parsing markets from the Kalshi API.

---

## Root Cause

The Kalshi API returns markets with `status: "initialized"` for new markets that haven't opened yet. Our enum only included:
- `active`
- `closed`
- `determined`
- `finalized`

---

## Error Message

```
ValidationError: 1 validation error for Market
status
  Input should be 'active', 'closed', 'determined' or 'finalized'
  [type=enum, input_value='initialized', input_type=str]
```

---

## Fix Applied

Added `INITIALIZED = "initialized"` to the `MarketStatus` enum:

```python
# src/kalshi_research/api/models/market.py
class MarketStatus(str, Enum):
    INITIALIZED = "initialized"  # NEW - was missing
    ACTIVE = "active"
    CLOSED = "closed"
    DETERMINED = "determined"
    FINALIZED = "finalized"
```

---

## Verification

After fix:
```bash
uv run kalshi data sync-markets
# ✓ Synced 200 events and 100000 markets
```

---

## Why Tests Didn't Catch This

Unit tests use **mocked API responses** with known status values. The real API returns status values that weren't in our test fixtures.

**Solution:** Add integration tests that hit the real API (or use recorded responses with all possible status values).
