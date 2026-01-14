# BUG-080: Inconsistent Midpoint Calculation Methods

**Status:** Open
**Priority:** P4 (Cosmetic)
**Created:** 2026-01-13
**Found by:** Deep Audit
**Effort:** ~15 min

---

## Summary

The codebase has two different midpoint calculation methods that can produce different results for the same inputs:

1. **Market model** (`src/kalshi_research/api/models/market.py:340`): Float division
2. **CLI display** (`src/kalshi_research/cli/scan.py:103`): Integer division with rounding

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
- `kalshi scan new-markets` rounds to whole cents for display, while calculations elsewhere can use the raw
  `Market.midpoint` float (which can be `.5` cents).

---

## Recommended Fix

Pick one convention for **CLI display**, and apply it consistently:

### Option A (keep integer cents, current behavior)
Keep whole-cents display and use an explicit “half-up” rule:

```python
# In cli/scan.py
def _market_yes_price_display(market: Market) -> str:
    bid = market.yes_bid_cents
    ask = market.yes_ask_cents
    if bid == 0 and ask == 0:
        return "[NO QUOTES]"
    if bid == 0 and ask == 100:
        return "[AWAITING PRICE DISCOVERY]"
    # Half-up display rounding (49.5 -> 50, 50.5 -> 51)
    midpoint_cents = int(market.midpoint + 0.5)
    return f"{midpoint_cents}¢"
```

### Option B (show half-cents when needed)
Show `x.5¢` for half-cent midpoints to match `Market.midpoint` exactly (no rounding).

---

## Verification

```python
# Given yes_bid=49, yes_ask=50 -> Market.midpoint == 49.5
# Option A expected display: "50¢"
# Option B expected display: "49.5¢"
```

---

## Notes

- The Orderbook model in `src/kalshi_research/api/models/orderbook.py` correctly uses `Decimal` for precision
- The Market model could be upgraded to use `Decimal` for consistency, but float is acceptable for typical use cases
