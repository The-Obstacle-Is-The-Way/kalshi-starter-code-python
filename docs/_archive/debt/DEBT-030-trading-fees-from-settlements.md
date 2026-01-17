# DEBT-030: Trading Fees Missing from P&L (Must Use Settlement Records)

**Priority:** P1 (Financial accuracy - understating losses)
**Status:** ✅ Resolved (2026-01-16)
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
- When positions are closed via trades (not held to settlement), we previously skipped settlement reconciliation and lost the fees
- **Fix:** apply settlement `fee_cost_dollars` once per ticker as a trading cost, regardless of whether the position was closed via trades or held to settlement

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

## Implemented Fix

### Apply Trading Fees From Settlement Records (SSOT-aligned)

Even when trades closed all lots, apply `fee_cost_dollars` from the settlement record as a trading cost:

```python
def calculate_summary_with_trades(...):
    # ... existing FIFO processing ...

    # Step 3: Apply trading fees even for trade-closed positions
    for settlement in settlements:
        fee_cents = self._parse_settlement_fee_cents(settlement.fee_cost_dollars)
        if fee_cents > 0:
            # Subtract from realized P&L (fees are costs)
            total_fees_from_settlements += fee_cents

    realized = sum(closed_trades) - total_fees_from_settlements
```

**Implementation:** `src/kalshi_research/portfolio/pnl.py` now subtracts the sum of settlement
`fee_cost_dollars` from realized P&L for the requested tickers, regardless of whether settlement
synthetic fills were generated.

---

## Verification (Local DB)

After fix, P&L matches Kalshi ROI for the known repro tickers:

| Ticker | P&L (Net, includes fees) |
|--------|--------------------------|
| KXTRUMPMENTION-26JAN15-CRED | -$77.82 |
| KXTRUMPMENTION-26JAN15-SOMA | -$84.31 |
| **Total** | **-$162.13** |

---

## Notes / Cleanup

- `PnLCalculator._synthesize_settlement_closes()` no longer attaches fees to synthetic settlement fills.
- Fee-related comments were updated to refer to **trading fees** (not “settlement fees”).

---

## Deferred Options (Not Needed For This Fix)

### Parse Fees from Fills API (If Available)

Investigate whether the fills API actually returns fees in some field we're not parsing. Check:
- `taker_fee` / `maker_fee` fields
- Nested response structure
- Different API versions

### Option C: Compute Fees from Formula

Kalshi's fee formula is documented:
```text
fee = round_up(0.035 × contracts × price × (1 - price))
```

We could compute fees ourselves, but this is fragile if Kalshi changes their formula.

---

## Implementation Checklist

- [x] Verify fills API response structure (no per-fill fee fields in our Fill model)
- [x] Apply settlement `fee_cost_dollars` even when trades closed all lots
- [x] Add test: positions closed via trades include settlement trading fees
- [x] Verify against known data: SOMA + CRED show -$162.13 net
- [x] Update DEBT-029 to clarify trading fees vs settlement handling

---

## Verification

After fix, P&L should match Kalshi's ROI:

| Ticker | Expected P&L |
|--------|-------------|
| SOMA + CRED (Trump Speech) | -$162.13 |

---

## Cleanup Required (DEBT-029 Interaction)

DEBT-029 implemented "settlement-as-synthetic-fill" reconciliation for markets held to settlement.
This debt clarifies that `fee_cost_dollars` should be treated as **total trading fees** (not a
separate settlement fee) and applied independently of the synthetic close logic.

### What Changes

| Component | Current State | After Fix |
|-----------|--------------|-----------|
| `_allocate_settlement_fee_cents()` | Prorates fees across YES/NO synthetic fills | **May be unnecessary** - just subtract total from P&L |
| `_synthesize_settlement_closes()` | Puts fees on synthetic fills | Should only apply for positions actually held to settlement |
| `calculate_summary_with_trades()` | Skips settlements if trades closed all lots | **Must still apply `fee_cost_dollars`** for trade-closed positions |

### Simplified Mental Model

```text
fee_cost_dollars = Total trading fees for this ticker (buys + sells)

If you closed via trades:
  → FIFO P&L is correct for price gains/losses
  → Subtract fee_cost_dollars (your trading costs)

If you held to settlement:
  → Synthesize settlement closes at 100c/0c
  → Subtract fee_cost_dollars (your trading costs)
```

### Dead Code After Fix?

Resolved:
- [x] Synthetic settlement fills no longer carry fees
- [x] Comments updated to reference trading fees

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
