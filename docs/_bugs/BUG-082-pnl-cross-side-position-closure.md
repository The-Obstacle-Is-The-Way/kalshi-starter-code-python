# BUG-082: P&L Calculator Ignores Cross-Side Position Closure

**Status:** Open
**Priority:** P0 (Critical - financial calculation error)
**Component:** `src/kalshi_research/portfolio/pnl.py`
**Found:** 2026-01-14
**Reporter:** User via Claude Code session

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

In `pnl.py:56-68`:

```python
ticker_side_trades: dict[tuple[str, str], list[Trade]] = {}
for trade in trades:
    key = (trade.ticker, trade.side)  # ← Groups YES and NO separately!
    ticker_side_trades.setdefault(key, []).append(trade)
```

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

## Correct Fix: Normalize Trades to YES-Equivalent

The FIFO should normalize all trades to a single reference side (YES):

```python
# Normalize all trades to YES-equivalent before FIFO matching
#
# Key insight: On Kalshi, YES + NO always = $1.00
# When you hold YES and trade NO, Kalshi NETS them (position goes to 0)
#
# For FIFO (long YES tracking):
# - BUY YES: Opens/increases long
# - SELL YES: Closes/decreases long
# - BUY NO: Closes long (you're betting against YES, exits your YES position)
# - SELL NO: Closes long (counterparty buys NO, Kalshi nets against your YES)
#
# Both NO trades CLOSE your YES position, just at different effective prices.
# This is because Kalshi nets positions, not because of complex economics.

def normalize_trade_to_yes(trade: Trade) -> NormalizedTrade:
    if trade.side == "yes":
        # YES trades stay as-is
        return NormalizedTrade(
            ticker=trade.ticker,
            action=trade.action,  # buy or sell
            price_cents=trade.price_cents,
            quantity=trade.quantity,
            ...
        )
    else:
        # NO trades: both close YES positions at inverted price
        inverted_price = 100 - trade.price_cents
        return NormalizedTrade(
            ticker=trade.ticker,
            action="sell",  # Both NO actions = close YES long
            price_cents=inverted_price,
            quantity=trade.quantity,
            ...
        )

# NOTE: This assumes user is primarily trading YES (long-only strategy).
# Edge case NOT handled: opening pure NO positions without YES to net against.
# For complete handling, would need to track both YES and NO positions separately.
```

### Conversion Rules

**Key insight:** On Kalshi, selling NO against an existing YES position **closes** the YES position. Kalshi nets YES and NO to produce position=0.

| Original Trade | Normalized (YES-Equivalent) | Economic Meaning |
|----------------|------------------------------|------------------|
| BUY YES @ 50¢ | BUY @ 50¢ | Open long at 50¢ |
| SELL YES @ 60¢ | SELL @ 60¢ | Close long at 60¢ |
| **SELL NO @ 85¢** | **SELL @ 15¢** | **Close long at 15¢** (Kalshi nets your YES against buyer's NO) |
| **BUY NO @ 75¢** | **SELL @ 25¢** | **Close long at 25¢** (or open short if no YES position) |

**Verification against user's trades:**
- Bought 189 YES @ 51¢ = paid $96.52
- Sold 189 NO @ 85¢ = effectively sold YES @ 15¢
- P&L per contract = 15¢ - 51¢ = -36¢
- Total P&L = -36¢ × 189 = -$68.04 (before fees)
- Kalshi reports: -$73.07 (difference is ~$5 in fees) ✓

### Why This Works

After normalization, FIFO operates on a single dimension:
- All BUYs open/increase position
- All SELLs close/decrease position
- Price is always YES-equivalent (0-100 scale)

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

- [ ] FIFO normalizes all trades to YES-equivalent before matching
- [ ] `Orphan sell qty skipped` drops to 0 for cross-side closures
- [ ] User's -$153.49 loss appears correctly
- [ ] Trade count shows actual closed trades
- [ ] Unit tests cover all 4 trade type combinations
- [ ] Sanity check compares our P&L to Kalshi's when available

---

## Test Cases

```python
def test_pnl_normalize_buy_yes():
    """BUY YES stays as-is."""
    trade = Trade(side="yes", action="buy", price_cents=50, ...)
    normalized = normalize_trade_to_yes(trade)
    assert normalized.action == "buy"
    assert normalized.price_cents == 50


def test_pnl_normalize_sell_no():
    """SELL NO becomes SELL YES at inverted price (closing long)."""
    trade = Trade(side="no", action="sell", price_cents=85, ...)
    normalized = normalize_trade_to_yes(trade)
    assert normalized.action == "sell"  # SELL NO = SELL YES (close)
    assert normalized.price_cents == 15  # 100 - 85


def test_pnl_normalize_buy_no():
    """BUY NO becomes SELL YES at inverted price (closing long or opening short)."""
    trade = Trade(side="no", action="buy", price_cents=75, ...)
    normalized = normalize_trade_to_yes(trade)
    assert normalized.action == "sell"  # BUY NO = SELL YES equivalent
    assert normalized.price_cents == 25  # 100 - 75


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
