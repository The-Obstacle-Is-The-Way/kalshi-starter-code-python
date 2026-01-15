# BUG-082: P&L Calculator Ignores Cross-Side Position Closure

**Status:** ✅ Resolved
**Priority:** P0 (Critical - financial calculation error)
**Component:** `src/kalshi_research/portfolio/pnl.py`
**Found:** 2026-01-14
**Reporter:** User via Claude Code session
**Fixed:** 2026-01-14
**Archived:** 2026-01-14

---

## Summary

The P&L calculator fails to recognize that on Kalshi, **selling NO closes a YES position** (and vice versa). This causes realized P&L to be drastically underreported.

---

## Why We Compute Our Own P&L (SSOT Analysis)

**This is NOT a case of "we should just use Kalshi's number."**

### Vendor Doc Says: Compute From Local History

From `kalshi-api-reference.md` (lines 438-441):

> `realized_pnl` is a market-level "locked in P&L" field (cents) per the OpenAPI schema. Kalshi's docs do **not specify whether `/portfolio/positions` returns closed markets (`position = 0`)**, so **do not assume it is a complete "all time realized P&L" feed. For end-to-end realized P&L across your history, sync `/portfolio/fills` AND `/portfolio/settlements` and compute from local history (handling gaps explicitly).**

### Vendor Doc Warns About Our Exact Bug

From `kalshi-api-reference.md` (lines 479-480):

> **Cross-Side Closing:** The `side` field is **literal** (the side you traded), NOT the effective position side. Selling YES to close a NO position shows `side=yes`, **which can confuse FIFO calculations.**

### Conclusion: We Need FIFO, But It's Broken

1. **We NEED our own P&L calculation** - Kalshi's `realized_pnl` is not guaranteed complete
2. **Our FIFO is broken** - doesn't handle cross-side closure
3. **The vendor doc PREDICTED this bug** - we just never fixed it

---

## Historical Context: BUG-060

BUG-060 asked "why don't we just use Kalshi's `realized_pnl`?" and was correctly closed as "not a bug" because:

- Kalshi's value isn't guaranteed complete
- We need fills + settlements sync
- SSOT says compute locally

But BUG-060 **did not fix cross-side closure** - it just made the FIFO gracefully skip orphan sells (the `orphan_sell_qty_skipped` counter).

---

## Root Cause

### FIFO Groups by Side (Broken)

Previously, in `pnl.py`, FIFO grouped fills by `(ticker, side)` using the **literal** `side` from `/portfolio/fills`.
Kalshi warns that `side` is literal and can represent closes on the opposite side, so this grouping can create
"orphan sells" even when the position is actually being closed.

**Fix:** Normalize fills into an "effective" `(ticker, side)` stream before FIFO matching:
- BUY trades: affect the literal side at the literal price.
- SELL trades: affect the *opposite* side at the *inverted* price (`100 - price_cents`).

- BUY YES → group `(TICKER, yes)`
- SELL NO → group `(TICKER, no)` ← Never matches YES buys!

### Impact

User executed these trades on 2026-01-14:

| Ticker | Side | Action | Qty | Price |
|--------|------|--------|-----|-------|
| KXTRUMPMENTION-26JAN15-CRED | YES | BUY | 189 | ~51¢ |
| KXTRUMPMENTION-26JAN15-CRED | NO | SELL | 189 | ~85¢ |
| KXTRUMPMENTION-26JAN15-SOMA | YES | BUY | 168 | ~58¢ |
| KXTRUMPMENTION-26JAN15-SOMA | NO | SELL | 168 | ~85¢ |

**Kalshi's `realized_pnl` (stored in positions):**
- CRED: -$73.07
- SOMA: -$80.42
- **Total: -$153.49** ✓

**Our FIFO calculation:**
- Realized: -$55.49 ✗
- `Orphan sell qty skipped: 500` ← All NO sells skipped!

---

## NOT Multivariate-Specific

All 5 positions with cross-side trades are affected:

| Ticker | Trade Types | Market Type |
|--------|-------------|-------------|
| KXTRUMPMENTION-26JAN15-CRED | yes_buy, no_sell | MVE |
| KXTRUMPMENTION-26JAN15-SOMA | yes_buy, no_sell | MVE |
| KXNFLAFCCHAMP-25-DEN | yes_buy, no_sell | Sports |
| KXSB-26-DEN | yes_buy, no_sell | Sports |
| KXNCAAFSPREAD-26JAN09OREIND-IND3 | no_buy, yes_sell | Spread |

---

## Correct Fix: Normalize Trades to an Effective Side (Both Directions)

The FIFO must normalize fills so that the close leg is attributed to the correct side (YES or NO) and priced correctly.

```python
def normalize_for_fifo(trade: Trade) -> NormalizedTrade:
    if trade.action == "buy":
        # BUY affects the literal side at the literal price.
        return NormalizedTrade(side=trade.side, action="buy", price_cents=trade.price_cents, ...)

    # SELL closes the opposite side at the inverted price.
    inverted_price = 100 - trade.price_cents
    opposite_side = "no" if trade.side == "yes" else "yes"
    return NormalizedTrade(side=opposite_side, action="sell", price_cents=inverted_price, ...)
```

### Conversion Rules

This captures both observed close patterns:

| Open | Close (as seen in fills) | Effective Close (for FIFO) |
|---|---|---|
| BUY YES @ `yes_price` | SELL NO @ `no_price` | SELL YES @ `100 - no_price` |
| BUY NO @ `no_price` | SELL YES @ `yes_price` | SELL NO @ `100 - yes_price` |

This aligns with the vendor warning that `side` is literal, and with real synced history in `data/kalshi.db`.

**Verification against user's trades (exact, from local DB):**
- `KXTRUMPMENTION-26JAN15-CRED`: -$73.07
- `KXTRUMPMENTION-26JAN15-SOMA`: -$80.42
- Total: -$153.49

### Why This Works

After normalization, FIFO sees a consistent stream where buys and sells operate on the same `(ticker, side)` inventory,
so closes are matched and priced correctly.

---

## What About Kalshi's `realized_pnl`?

### Use It As a Sanity Check

After implementing the fix, compare our calculated P&L to Kalshi's reported value:

```python
kalshi_pnl = sum(pos.realized_pnl_cents for pos in positions)
our_pnl = fifo_result.total_realized_cents

if abs(kalshi_pnl - our_pnl) > threshold:
    logger.warning(
        f"P&L discrepancy: Kalshi={kalshi_pnl}, Ours={our_pnl}, "
        f"Delta={kalshi_pnl - our_pnl}"
    )
```

### Don't Rely On It As Primary

Per SSOT, Kalshi's value may be incomplete for:
- Closed positions no longer in API response
- Historical positions before our sync started
- Edge cases in their calculation

---

## Acceptance Criteria

- [x] FIFO normalizes trades before matching
- [x] `Orphan sell qty skipped` drops to 0 for cross-side closures
- [x] User's -$153.49 loss appears correctly
- [x] Trade count shows actual closed trades
- [x] Unit tests cover cross-side close in both directions

---

## Test Cases

```python
def test_pnl_normalize_sell_no():
    """SELL NO closes YES at inverted price."""
    trade = Trade(side="no", action="sell", price_cents=85, ...)
    normalized = normalize_for_fifo(trade)
    assert normalized.side == "yes"
    assert normalized.action == "sell"
    assert normalized.price_cents == 15


def test_pnl_cross_side_buy_yes_sell_no():
    """Full integration: BUY YES + SELL NO = closed position."""
    trades = [
        Trade(side="yes", action="buy", quantity=100, price_cents=50, ...),
        Trade(side="no", action="sell", quantity=100, price_cents=85, ...),
    ]
    calc = PnLCalculator()
    result = calc._get_closed_trade_pnls_fifo(trades)

    # After normalization:
    # - BUY @ 50¢ (open long)
    # - SELL @ 15¢ (SELL NO @ 85 → SELL YES @ 15, close long)
    # Loss = (50 - 15) * 100 = 3500 cents = $35
    assert result.closed_pnls == [-3500]
    assert result.orphan_sell_qty_skipped == 0


def test_pnl_cross_side_buy_no_sell_yes():
    """Full integration: BUY NO + SELL YES = closed position."""
    trades = [
        Trade(side="no", action="buy", quantity=100, price_cents=70, ...),
        Trade(side="yes", action="sell", quantity=100, price_cents=80, ...),
    ]
    calc = PnLCalculator()
    result = calc._get_closed_trade_pnls_fifo(trades)
    # Effective NO close price = 100 - 80 = 20
    assert result.closed_pnls == [(20 - 70) * 100]
```

---

## Related

- **BUG-060**: "Why don't we just use Kalshi's P&L?" - Correctly closed as "not a bug" because SSOT says compute locally. But didn't fix cross-side.
- **BUG-057**: FIFO P&L integrity - fixed crashes, not cross-side
- **BUG-058**: FIFO crash on incomplete history - fixed
- **BUG-059**: Missing settlements - fixed
- **SSOT**: `docs/_vendor-docs/kalshi-api-reference.md` lines 438-441, 479-480

---

## Investigation Notes (2026-01-14)

### Key SSOT Findings

1. **Vendor doc explicitly requires local computation** (line 441):
   > "For end-to-end realized P&L across your history, sync `/portfolio/fills` AND `/portfolio/settlements` and compute from local history"

2. **Vendor doc explicitly warns about cross-side** (line 479):
   > "The `side` field is **literal**... can confuse FIFO calculations"

3. **Kalshi's `realized_pnl` is not complete** (line 438):
   > "do not assume it is a complete 'all time realized P&L' feed"

### Why This Wasn't Caught Earlier

- BUG-060 correctly identified we need local computation
- BUG-057/058/059 fixed FIFO crashes and missing data
- But no one implemented the cross-side normalization
- The "orphan sell" graceful degradation masked the problem
