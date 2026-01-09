# BUG-048: Negative Liquidity Validation Error

**Priority**: Medium
**Status**: Active
**Created**: 2026-01-09

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

## Workaround

Use `--max-pages` to limit pagination and avoid hitting the problematic markets.

## Fix Options

1. Change `liquidity: int = Field(ge=0)` to just `liquidity: int` (allow negative)
2. Use a validator that coerces negative values to 0
3. Filter out invalid markets at the API layer

## Related Files

- `src/kalshi_research/api/models/market.py`
- `src/kalshi_research/api/client.py:159`
