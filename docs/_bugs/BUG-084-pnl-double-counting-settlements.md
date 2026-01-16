# BUG-084: P&L Double-Counting Between Trades and Settlements

**Priority:** P0 (Critical - financial calculations incorrect)
**Status:** Open
**Found:** 2026-01-16
**Location:** `src/kalshi_research/portfolio/pnl.py:278`

---

## Summary

The P&L calculator double-counts realized losses by summing BOTH the FIFO trade P&L AND the settlement P&L.
These represent the SAME economic activity, causing reported losses to be ~2-4x higher than actual.

**Impact:** User reported -$749 realized P&L when actual loss was ~$150.

---

## Evidence

### User's Trump Speech Trades (2026-01-14)

**Actual trades:**
- Bought 168 YES on SOMA at avg 58¢ = $97.08
- Bought 189 YES on CRED at avg 51¢ = $96.52
- Total invested: **$193.60**

**What user reported:**
- Put in ~$200, left with ~$60
- Actual loss: **~$140**

**What CLI shows:**
```bash
$ uv run kalshi portfolio pnl -t KXTRUMPMENTION-26JAN15-SOMA
Realized P&L: $-332.73

$ uv run kalshi portfolio pnl -t KXTRUMPMENTION-26JAN15-CRED
Realized P&L: $-339.89
```

Total reported: **-$672.62** (4.8x the actual ~$140 loss!)

---

## Root Cause

### pnl.py:278 - Double counting
```python
closed_trades = fifo_result.closed_pnls + settlement_pnls
```

This line **ADDS** the FIFO trade P&L to the settlement P&L. But these represent the SAME economic activity:

1. **FIFO Trade P&L** (from `_get_closed_trade_pnls_fifo`):
   - Tracks buy YES → sell NO (normalized to sell YES)
   - Correctly calculates: bought at X, sold at Y, P&L = Y - X

2. **Settlement P&L** (from settlement loop):
   - Tracks the SAME positions at settlement
   - Formula: `revenue - yes_total_cost - no_total_cost - fees`

When both are summed, the loss is counted twice (or more).

### pnl.py:271-276 - Settlement formula may also be wrong

```python
settlement_pnls.append(
    settlement.revenue
    - settlement.yes_total_cost
    - settlement.no_total_cost
    - fee_cents
)
```

For trades where user sold NO (cross-side closure), this formula subtracts `no_total_cost` (money received from selling) instead of treating it as revenue.

---

## Database Evidence

**portfolio_settlements table:**
```
SOMA: yes_total_cost=9708, no_total_cost=15134, revenue=0
CRED: yes_total_cost=9652, no_total_cost=16555, revenue=0
```

**trades table:**
- Buy YES trades: ~$193.60 total
- Sell NO trades: ~$316.89 total (but this is misleading - see normalization)

The settlement and trades are recording the SAME underlying positions.

---

## Proposed Fix

**Option A: Use ONLY settlement P&L for resolved markets (preferred)**
- If a ticker has a settlement record, use ONLY that for P&L
- Use FIFO trades only for positions that haven't settled yet
- Need to deduplicate by ticker

**Option B: Use ONLY FIFO trades**
- Remove settlement P&L calculation entirely
- FIFO already captures all buy/sell activity including cross-side closures

**Option C: Fix deduplication logic**
- Filter out trades for tickers that have settlements
- Requires careful handling of partial fills

---

## Verification Steps

1. Get user's actual Kalshi balance history to confirm real P&L
2. Calculate expected P&L manually:
   - SOMA: Bought 168 YES @ 58¢ = $97.08, market resolved NO, loss = $97.08
   - CRED: Bought 189 YES @ 51¢ = $96.52, market resolved NO, loss = $96.52
   - Total expected loss: ~$193.60 (or less if they exited early)

3. User says they got back $60 from $200 invested → loss = $140
   - This suggests they may have exited BEFORE settlement, capturing some value

---

## Related Issues

- BUG-060 (Closed): "Duplicate realized P&L computation (ignores Kalshi's value)" - may be related
- BUG-057: "Portfolio P&L integrity (FIFO realized P&L + unknown handling)" - was thought to be fixed

---

## Test Coverage Needed

1. Test that settled tickers are NOT double-counted
2. Test cross-side closure (buy YES, sell NO) P&L calculation
3. Test that reported P&L matches actual money in/out

---

## Affected Commands

- `kalshi portfolio pnl` - Shows inflated losses
- `kalshi portfolio pnl -t TICKER` - Shows inflated losses per ticker

---

## Workaround

Until fixed, manually calculate P&L from Kalshi web interface account history.
