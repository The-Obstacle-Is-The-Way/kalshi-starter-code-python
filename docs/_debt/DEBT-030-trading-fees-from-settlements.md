# DEBT-030: Trading Fees Missing from P&L (Must Use Settlement Records)

**Priority:** P1 (Financial accuracy - understating losses)
**Status:** Open
**Created:** 2026-01-16
**Related:** [DEBT-029](DEBT-029-settlement-synthetic-fill-reconciliation.md), [Kalshi Fee Schedule](https://kalshi.com/fee-schedule)

---

## Why This Is Critical

This is a **P1 financial accuracy bug** in a trading application:

1. **P&L is wrong** - We're understating losses by ~5% (the fee percentage)
2. **Tax implications** - Fees are deductible trading costs; incorrect reporting = incorrect taxes
3. **Strategy evaluation** - If you think you lost $153 but actually lost $162, your edge calculations are off
4. **Trust** - A financial app that can't accurately report P&L is fundamentally broken

**Discovery cost:** ~$150 in real trading losses (a $150 bug bounty, if you will)

---

## Summary

**Our P&L is missing trading fees**, causing us to understate losses.

- Kalshi's fills API does not return per-trade fees
- We hardcode `fee_cents=0` for all trades (`syncer.py:287`)
- The settlement record's `fee_cost_dollars` contains the **total trading fees** (NOT a settlement fee)
- When positions are closed via trades (not held to settlement), we skip the settlement record entirely
- **Result: Trading fees are never applied to P&L**

---

## Evidence (Real User Data)

### Kalshi Order History (Source of Truth)

| Ticker | Action | Qty | Amount | **Fee** |
|--------|--------|-----|--------|---------|
| CRED | Bought YES | 189 | $99.83 | **$3.31** |
| CRED | Sold YES | 189 | $22.01 | **$1.44** |
| SOMA | Bought YES | 168 | $99.95 | **$2.87** |
| SOMA | Sold YES | 168 | $15.64 | **$1.02** |
| **Total** | | | | **$8.64** |

### Our Database

```sql
-- Trades have fee_cents=0
SELECT ticker, SUM(fee_cents) FROM trades WHERE ticker LIKE '%TRUMPMENTION%' GROUP BY ticker;
-- Result: 0 for all

-- Settlements have fee_cost_dollars
SELECT ticker, fee_cost_dollars FROM portfolio_settlements WHERE ticker LIKE '%TRUMPMENTION%';
-- CRED: $4.75, SOMA: $3.89 = $8.64 total (MATCHES!)
```

### P&L Discrepancy

| Source | P&L |
|--------|-----|
| Our calculation (FIFO, no fees) | -$153.49 |
| Settlement fees we're missing | -$8.64 |
| **True P&L** | **-$162.13** |
| **Kalshi ROI (verified)** | **-$162.13** |

---

## Root Cause

### syncer.py:287

```python
Trade(
    ...
    fee_cents=0,  # API doesn't always provide per-trade fees in fills
    ...
)
```

The fills API response doesn't include per-trade fees. The comment acknowledges this, but the workaround (hardcoding 0) is incorrect.

### Kalshi's Fee Reporting Model

Per [Kalshi Help Center](https://help.kalshi.com/trading/fees):
> "There is no settlement fee."

The settlement record's `fee_cost_dollars` is **not** a settlement fee - it's a **summary of all trading fees** for that ticker. This is where Kalshi reports the fees, not in the fills API.

### pnl.py Current Behavior

When positions are closed via trades:
1. FIFO processes trades → closes all lots → `open_lots` is empty
2. Settlement is skipped because no open lots remain
3. `fee_cost_dollars` is never applied
4. **Fees are lost**

---

## Proposed Fix

### Option A: Apply Settlement Fees to Trade-Closed Positions (Recommended)

Even when trades closed all lots, apply `fee_cost_dollars` from the settlement record:

```python
def calculate_summary_with_trades(...):
    # ... existing FIFO processing ...

    # Step 3: Apply settlement fees even for trade-closed positions
    for settlement in settlements:
        fee_cents = self._parse_settlement_fee_cents(settlement.fee_cost_dollars)
        if fee_cents > 0:
            # Subtract from realized P&L (fees are costs)
            total_fees_from_settlements += fee_cents

    realized = sum(closed_trades) - total_fees_from_settlements
```

### Option B: Parse Fees from Fills API (If Available)

Investigate whether the fills API actually returns fees in some field we're not parsing. Check:
- `taker_fee` / `maker_fee` fields
- Nested response structure
- Different API versions

### Option C: Compute Fees from Formula

Kalshi's fee formula is documented:
```
fee = round_up(0.035 × contracts × price × (1 - price))
```

We could compute fees ourselves, but this is fragile if Kalshi changes their formula.

---

## Implementation Checklist

- [ ] Verify fills API response structure (does it have fee fields we're missing?)
- [ ] If no fees in fills API: Apply settlement `fee_cost_dollars` for trade-closed positions
- [ ] Update `_get_closed_trade_pnls_fifo` or `calculate_summary_with_trades` to include fees
- [ ] Add test: Positions closed via trades should include settlement fees in P&L
- [ ] Verify against known data: SOMA + CRED should show -$162.13
- [ ] Update DEBT-029 to clarify settlement fees vs trading fees

---

## Verification

After fix, P&L should match Kalshi's ROI:

| Ticker | Expected P&L |
|--------|-------------|
| SOMA + CRED (Trump Speech) | -$162.13 |

---

## Cleanup Required (DEBT-029 Interaction)

DEBT-029 implemented "settlement-as-synthetic-fill" with fee proration. That work assumed `fee_cost_dollars` was a settlement-specific fee. **We now know it's actually the total trading fees.**

### What Changes

| Component | Current State | After Fix |
|-----------|--------------|-----------|
| `_allocate_settlement_fee_cents()` | Prorates fees across YES/NO synthetic fills | **May be unnecessary** - just subtract total from P&L |
| `_synthesize_settlement_closes()` | Puts fees on synthetic fills | Should only apply for positions actually held to settlement |
| `calculate_summary_with_trades()` | Skips settlements if trades closed all lots | **Must still apply `fee_cost_dollars`** for trade-closed positions |

### Simplified Mental Model

```
fee_cost_dollars = Total trading fees for this ticker (buys + sells)

If you closed via trades:
  → FIFO P&L is correct for price gains/losses
  → Subtract fee_cost_dollars (your trading costs)

If you held to settlement:
  → Synthesize settlement closes at 100c/0c
  → Subtract fee_cost_dollars (your trading costs)
```

### Dead Code After Fix?

Once fixed, we should audit whether these are still needed:
- [ ] `_allocate_settlement_fee_cents()` - possibly remove if we just subtract total
- [ ] Fee fields on synthetic fills - possibly remove if fees are applied separately
- [ ] Comments referencing "settlement fees" - update to "trading fees"

---

## Lessons Learned

1. **Verify against source of truth early** - We built complex fee proration logic without verifying what `fee_cost_dollars` actually meant
2. **Real user data catches real bugs** - The Trump speech trades ($150 loss) revealed this
3. **"API doesn't provide X" isn't an excuse** - If the API doesn't give fees per-trade, find where it DOES report them
4. **Financial accuracy is non-negotiable** - A 5% error in a trading app is a showstopper

---

## Sources

- [Kalshi Fee Schedule](https://kalshi.com/fee-schedule)
- [Kalshi Fees Help Center](https://help.kalshi.com/trading/fees) - "There is no settlement fee"
- User's Kalshi order history (verified $8.64 in trading fees)
- User's Kalshi ROI display (verified -$162.13)
