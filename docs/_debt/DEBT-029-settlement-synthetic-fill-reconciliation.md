# DEBT-029: Settlement-as-Synthetic-Fill Reconciliation

**Priority:** P2 (Correctness - affects edge cases, current workaround is safe)
**Status:** ✅ Implemented (2026-01-16)
**Created:** 2026-01-16
**Related:** [BUG-084](../_archive/bugs/BUG-084-pnl-double-counting-settlements.md) (original workaround)

---

## Summary

Before DEBT-029, the P&L calculation used a **deduplication workaround** (skip settlements when trades closed all lots)
instead of the **proper reconciliation approach** where settlements are converted to synthetic closing fills per
Kalshi's documented behavior.

**Now:** Implemented settlement-as-synthetic-fill reconciliation (including scalar settlements).

---

## Problem Statement

### Previous Implementation (BUG-084 Workaround)

```python
# pnl.py:282-286
if (
    settlement.ticker in trades_tickers
    and open_qty_by_ticker.get(settlement.ticker, 0) <= 0
):
    continue  # Skip settlement if no open lots
```

This **avoids double-counting** but doesn't properly model what settlements represent.

### What Kalshi Docs Say (SSOT)

From `docs/_vendor-docs/kalshi-api-reference.md:914-917`:

> **Settlements act as "sells" at the settlement price (100c if won, 0c if lost)**

Settlements are **synthetic closing trades** at the settlement price:
- Market resolves YES → Your YES contracts "sell" at 100c, NO contracts "sell" at 0c
- Market resolves NO → Your YES contracts "sell" at 0c, NO contracts "sell" at 100c

### Why This Matters

| Scenario | Current Fix | Proper Fix |
|----------|-------------|------------|
| Full trade history, exited before settlement | ✅ Correct | ✅ Correct |
| Held to settlement (no exit trades) | ⚠️ Uses raw settlement formula | ✅ Synthesizes fills |
| **Partial exit + held rest to settlement** | ⚠️ May be inaccurate | ✅ Correct |
| Gaps in fills history | ⚠️ Uncertain | ✅ Handles via settlements |

---

## Industry Best Practices

Per [Vanguard's FIFO documentation](https://investor.vanguard.com/investor-resources-education/taxes/cost-basis-first-in-first-out) and [Schwab's cost basis guide](https://www.schwab.com/learn/story/save-on-taxes-know-your-cost-basis):

1. **FIFO processes lots in acquisition order** - oldest lots sold first
2. **All dispositions must be recorded** - whether by sale, transfer, or settlement
3. **Cost basis must be tracked per-lot** - not averaged after the fact

For prediction markets, a settlement is economically equivalent to a forced sale at the binary outcome price.

---

## Implemented Approach

### Algorithm: Settlement-as-Synthetic-Fill

```python
def _synthesize_settlement_fills(
    self,
    settlements: list[PortfolioSettlement],
    open_lots: dict[tuple[str, str], _Lot],
) -> list[_EffectiveTrade]:
    """
    Convert settlements to synthetic closing fills for remaining open lots.

    Per Kalshi docs: "Settlements act as sells at the settlement price
    (100c if won, 0c if lost)"
    """
    synthetic_fills: list[_EffectiveTrade] = []

    for settlement in settlements:
        # Determine settlement prices based on market_result
        if settlement.market_result == "yes":
            yes_settlement_price = 100  # YES wins → YES sells at 100c
            no_settlement_price = 0     # YES wins → NO sells at 0c
        elif settlement.market_result == "no":
            yes_settlement_price = 0    # NO wins → YES sells at 0c
            no_settlement_price = 100   # NO wins → NO sells at 100c
        elif settlement.market_result == "scalar":
            # Scalar: settlement.value is the YES payout in cents (OpenAPI)
            yes_settlement_price = settlement.value
            no_settlement_price = 100 - settlement.value
        elif settlement.market_result == "void":
            # Void = refund at cost basis (effectively break-even)
            # Skip - no P&L impact
            continue
        else:
            # unknown - skip for now
            continue

        # Synthesize YES fill if open YES lots exist
        yes_key = (settlement.ticker, "yes")
        if yes_key in open_lots and open_lots[yes_key].qty_remaining > 0:
            synthetic_fills.append(_EffectiveTrade(
                ticker=settlement.ticker,
                side="yes",
                action="sell",
                quantity=open_lots[yes_key].qty_remaining,
                price_cents=yes_settlement_price,
                total_cost_cents=yes_settlement_price * open_lots[yes_key].qty_remaining,
                fee_cents=0,  # Settlement fees handled separately
                executed_at=settlement.settled_at,
            ))

        # Synthesize NO fill if open NO lots exist
        no_key = (settlement.ticker, "no")
        if no_key in open_lots and open_lots[no_key].qty_remaining > 0:
            synthetic_fills.append(_EffectiveTrade(
                ticker=settlement.ticker,
                side="no",
                action="sell",
                quantity=open_lots[no_key].qty_remaining,
                price_cents=no_settlement_price,
                total_cost_cents=no_settlement_price * open_lots[no_key].qty_remaining,
                fee_cents=0,
                executed_at=settlement.settled_at,
            ))

    return synthetic_fills
```

### Updated Flow

```
1. Process all fills via FIFO → get closed_pnls + open_lots
2. For each settlement with open lots:
   a. Synthesize closing fills at settlement price (100c/0c for binary, value/100-value for scalar)
   b. Process synthetic fills through FIFO (consuming remaining lots)
   c. Add resulting P&L to closed_pnls
3. Apply settlement fees from settlement.fee_cost_dollars (prorated across settled quantities)
4. Return unified P&L
```

### Benefits

1. **Single code path** - All P&L flows through FIFO, no special-case formulas
2. **Auditable** - Every P&L can be traced to a fill (real or synthetic)
3. **Correct for all scenarios** - Partial exits, held-to-settlement, gaps
4. **Matches vendor docs** - Implements exactly what Kalshi says settlements represent

---

## Implementation Checklist

- [x] Add `_synthesize_settlement_closes()` method to `PnLCalculator`
- [x] Add `_process_synthetic_fills()` method to `PnLCalculator`
- [x] Modify `calculate_summary_with_trades()` to use synthesis instead of raw formula
- [x] Handle edge case: settlements without corresponding trades (data gaps)
- [x] Add tests for:
  - [x] Held YES to YES settlement (100c payout)
  - [x] Held YES to NO settlement (0c payout)
  - [x] Held NO to YES settlement (0c payout)
  - [x] Held NO to NO settlement (100c payout)
  - [x] Partial exit + held rest to settlement
  - [x] Scalar settlement (YES payout = value, NO payout = 100-value)
  - [x] Settlement fee proration across sides
  - [x] Void settlement (break-even)
  - [x] Both sides hedged to settlement
- [x] Update docstrings with SSOT reference
- [x] Verify against current data (SOMA/CRED still show same P&L)

---

## Verification

After implementation, these should still match:

| Ticker | Current P&L | Expected P&L |
|--------|-------------|--------------|
| KXTRUMPMENTION-26JAN15-SOMA | -$80.42 | -$80.42 |
| KXTRUMPMENTION-26JAN15-CRED | -$73.07 | -$73.07 |
| Total Realized | -$174.43 | -$174.43 |

The fix should produce identical results for the current data (since trades closed all lots before settlement) while being correct for future scenarios.

---

## Risk Assessment

**Low risk** - This replaces the BUG-084 workaround with a single SSOT-aligned settlement reconciliation path.

---

## Sources

- [Kalshi API Reference - Settlements](../_vendor-docs/kalshi-api-reference.md)
- [Vanguard FIFO Cost Basis](https://investor.vanguard.com/investor-resources-education/taxes/cost-basis-first-in-first-out)
- [Charles Schwab Cost Basis Guide](https://www.schwab.com/learn/story/save-on-taxes-know-your-cost-basis)
- [BUG-084 Archive](../_archive/bugs/BUG-084-pnl-double-counting-settlements.md)
