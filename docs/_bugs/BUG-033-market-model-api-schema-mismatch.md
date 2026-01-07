# BUG-033: Market Model API Schema Mismatch

## Status: :yellow_circle: Open

## Priority: **CRITICAL** - Blocks all live API operations

## Summary

The `Market` Pydantic model has validation constraints that don't match actual Kalshi API responses, causing `ValidationError` on live data and blocking ALL scanner/collector operations.

## Root Cause

Two fields in `src/kalshi_research/api/models/market.py` are too restrictive:

### Issue 1: `liquidity` field rejects negative values

```python
# Line 66
liquidity: int = Field(..., ge=0, description="Dollar liquidity")
```

**API returns:** `liquidity: -170750` (negative value)
**Error:**
```
ValidationError: 1 validation error for Market
liquidity
  Input should be greater than or equal to 0 [type=greater_than_equal,
  input_value=-170750, input_type=int]
```

### Issue 2: `status` enum missing `inactive` value

```python
# Lines 12-19
class MarketStatus(str, Enum):
    INITIALIZED = "initialized"
    ACTIVE = "active"
    CLOSED = "closed"
    DETERMINED = "determined"
    FINALIZED = "finalized"
```

**API returns:** `status: "inactive"`
**Error:**
```
ValidationError: 1 validation error for Market
status
  Input should be 'initialized', 'active', 'closed', 'determined' or 'finalized'
  [type=enum, input_value='inactive', input_type=str]
```

## Impact

- **`kalshi scan opportunities`** - BROKEN
- **`kalshi scan arbitrage`** - BROKEN
- **`kalshi scan movers`** - BROKEN
- **`kalshi data collect`** - BROKEN
- Any operation that fetches live market lists from API fails

## Evidence

```bash
$ uv run kalshi scan opportunities --filter close-race --top 20 --min-volume 50
# ValidationError: liquidity >= 0 violated

$ uv run kalshi data collect --once
# ValidationError: status must be in ['initialized', 'active', ...]
```

## Recommended Fix

```python
# src/kalshi_research/api/models/market.py

class MarketStatus(str, Enum):
    INITIALIZED = "initialized"
    ACTIVE = "active"
    INACTIVE = "inactive"  # ADD THIS
    CLOSED = "closed"
    DETERMINED = "determined"
    FINALIZED = "finalized"

# ...

class Market(BaseModel):
    # ...
    # Remove ge=0 constraint - API can return negative liquidity
    liquidity: int = Field(..., description="Dollar liquidity (can be negative)")
```

## Acceptance Criteria

- [ ] All scanner commands work against live API
- [ ] `kalshi data collect --once` completes successfully
- [ ] Tests updated to cover edge cases

## Related

- Discovered during live API testing on 2026-01-07
- Ticker with negative liquidity: `KXPAYROLLS-26OCT-*` markets
- Ticker with `inactive` status: Soccer goal scorer markets
