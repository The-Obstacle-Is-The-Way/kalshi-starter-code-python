# BUG-048: Negative Liquidity Validation Error

**Priority**: Medium
**Status**: REOPENED - Previous fix was incorrect
**Created**: 2026-01-09
**Updated**: 2026-01-09

## Symptom

When running `scan opportunities` without `--max-pages`, the full market scan crashes with:

```
ValidationError: 1 validation error for Market
liquidity
  Input should be greater than or equal to 0 [type=greater_than_equal, input_value=-170750, input_type=int]
```

## Root Cause

The `Market` Pydantic model in `api/models/market.py` has a validator:
```python
liquidity: int = Field(ge=0)
```

But Kalshi API returns some markets with negative liquidity values (e.g., `-170750`).

## CRITICAL CONTEXT (from Kalshi API Changelog)

**The `liquidity` field is being DEPRECATED on January 15, 2026.**

From [Kalshi API Changelog](https://docs.kalshi.com/changelog):
> The deprecated cent-denominated price fields will be removed from Market responses.
> Users should migrate to `*_dollars` equivalents (e.g., `yes_bid_dollars`).

Affected fields being removed:
- `liquidity` ← This one
- `yes_bid`, `yes_ask`, `no_bid`, `no_ask`
- `last_price`, `previous_price`
- `notional_value`

## Why the Previous Fix Was Wrong

The previous fix just removed `ge=0` to accept any value. This is wrong because:

1. **Liquidity cannot be negative** - It represents order book depth (how much is available to trade)
2. **Negative values are garbage data** - Either API bug or sentinel value
3. **Blindly accepting bad data** corrupts our database and analytics
4. **The field is deprecated anyway** - We should handle it gracefully, not validate it strictly

## Correct Fix

### Step 1: Make liquidity optional with deprecation warning

```python
# In api/models/market.py
from typing import Annotated
from pydantic import Field, field_validator
import warnings

# Mark as optional - field is deprecated as of Jan 15, 2026
liquidity: int | None = Field(
    default=None,
    description="DEPRECATED: Use dollar-denominated fields. Removed Jan 15, 2026."
)

@field_validator("liquidity", mode="before")
@classmethod
def handle_deprecated_liquidity(cls, v: int | None) -> int | None:
    """Handle deprecated liquidity field gracefully."""
    if v is None:
        return None
    if v < 0:
        # Log warning but don't crash - field is deprecated anyway
        import logging
        logging.getLogger(__name__).warning(
            f"Received negative liquidity value: {v}. "
            "Treating as None. Field deprecated Jan 15, 2026."
        )
        return None
    return v
```

### Step 2: Update any code that uses liquidity

Search for usages and handle `None` case:
```python
# Before (crashes on None)
total_liquidity = market.liquidity * 100

# After (handles None)
total_liquidity = (market.liquidity or 0) * 100
```

### Step 3: Add TODO to migrate to dollar fields

Create TODO to migrate to `yes_bid_dollars`, `yes_ask_dollars` etc. before Jan 15, 2026.

## Definition of Done

- [ ] `liquidity` field is `int | None` (optional)
- [ ] Validator logs warning on negative values, returns `None`
- [ ] Any code using `liquidity` handles `None` case
- [ ] Added deprecation comment referencing Jan 15, 2026 removal
- [ ] Tests updated to verify negative → None behavior
- [ ] All quality gates pass

## Related Files

- `src/kalshi_research/api/models/market.py`
- `src/kalshi_research/api/client.py`
- `src/kalshi_research/analysis/scanner.py` (if uses liquidity)

## Sources

- [Kalshi API Changelog](https://docs.kalshi.com/changelog) - Deprecation notice
- [Kalshi API Documentation](https://docs.kalshi.com) - Field definitions
