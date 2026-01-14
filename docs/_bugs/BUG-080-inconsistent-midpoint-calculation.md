# BUG-080: Inconsistent Midpoint Calculation Methods

**Status:** Open
**Priority:** P4 (Cosmetic)
**Created:** 2026-01-13
**Found by:** Deep Audit
**Effort:** ~15 min

---

## Summary

The codebase has two different midpoint calculation methods that can produce different results for the same inputs:

1. **Market model** (`api/models/market.py:340`): Float division
2. **CLI display** (`cli/scan.py:103`): Integer division with rounding

---

## Impact

- **Severity:** Very Low - Display inconsistency only
- **Financial Impact:** None
- **User Impact:** Minor confusion if comparing outputs

Example with `yes_bid=49, yes_ask=50`:
- Market model: `(49 + 50) / 2 = 49.5` (float)
- CLI display: `(49 + 50 + 1) // 2 = 50` (rounded up integer)

---

## Root Cause

### Market model (float division)
At `src/kalshi_research/api/models/market.py:338-340`:

```python
@property
def midpoint(self) -> float:
    """Calculate midpoint from yes bid/ask using cents values."""
    return (self.yes_bid_cents + self.yes_ask_cents) / 2
```

### CLI display (integer division with round-up)
At `src/kalshi_research/cli/scan.py:103`:

```python
midpoint_cents = (bid + ask + 1) // 2
```

---

## Analysis

Both approaches are valid for their contexts:

1. **Float division** is correct for calculations where precision matters (P&L, arbitrage detection)
2. **Integer round-up** is reasonable for display where fractional cents don't exist

However, the inconsistency can cause confusion:
- Scanner might show "50¢" while other commands show "49.5¢"
- Comparisons between different command outputs may not match

---

## Recommended Fix

Standardize on float midpoint everywhere, with display-time rounding:

```python
# In cli/scan.py
def _market_yes_price_display(market: Market) -> str:
    bid = market.yes_bid_cents
    ask = market.yes_ask_cents
    if bid == 0 and ask == 0:
        return "[NO QUOTES]"
    if bid == 0 and ask == 100:
        return "[AWAITING PRICE DISCOVERY]"
    # Use consistent midpoint calculation, round for display
    midpoint_cents = round(market.midpoint)  # Uses Market.midpoint property
    return f"{midpoint_cents}¢"
```

This keeps the Market model as the single source of truth for midpoint calculation.

---

## Verification

```python
def test_midpoint_display_consistency():
    """Display should use Market.midpoint as source of truth."""
    market = make_market(yes_bid=49, yes_ask=50)
    display = _market_yes_price_display(market)
    assert display in ("49¢", "50¢")  # Either is acceptable after rounding
```

---

## Notes

- The Orderbook model in `api/models/orderbook.py` correctly uses `Decimal` for precision
- The Market model could be upgraded to use `Decimal` for consistency, but float is acceptable for typical use cases
