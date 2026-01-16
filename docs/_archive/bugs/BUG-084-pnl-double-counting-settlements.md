# BUG-084: P&L Double-Counting Between Trades and Settlements

**Priority:** P0 (Critical - financial calculations incorrect)
**Status:** ✅ Fixed (2026-01-16, dev `41d0c3a`)
**Found:** 2026-01-16
**Location:** `src/kalshi_research/portfolio/pnl.py:303` (`PnLCalculator.calculate_summary_with_trades`)

---

## Summary

Before the fix, `kalshi portfolio pnl` added two separate “realized P&L” streams:

1. FIFO realized P&L from fills (`trades` table) — correct for this DB.
2. A second value derived from `/portfolio/settlements` fields — currently **not a valid realized P&L
   figure** for our observed settlement rows.

Those values are summed together, producing materially inflated losses.

**Impact (verified on this DB):**
- Before fix: CLI realized P&L: **-$749.05**
- After fix: CLI realized P&L: **-$174.43**
- The two Trump tickers below: FIFO-only **-$153.49** vs CLI **-$672.62**

---

## Evidence

### User's Trump Speech Trades (2026-01-14)

**Actual trades:**
- Bought 168 YES on SOMA at avg 58¢ = $97.08
- Bought 189 YES on CRED at avg 51¢ = $96.52
- Total invested: **$193.60**

**Correct realized P&L (FIFO-only on this DB):**
- SOMA: **-$80.42**
- CRED: **-$73.07**
- Total: **-$153.49**

**Before fix, CLI showed:**
```bash
$ uv run kalshi portfolio pnl -t KXTRUMPMENTION-26JAN15-SOMA
Realized P&L: $-332.73

$ uv run kalshi portfolio pnl -t KXTRUMPMENTION-26JAN15-CRED
Realized P&L: $-339.89
```

Total reported: **-$672.62** (~4.4x the FIFO-only **-$153.49** loss).

---

## Root Cause

### pnl.py:278 - Double counting
```python
closed_trades = fifo_result.closed_pnls + settlement_pnls
```

This line **ADDS** the FIFO trade P&L to the settlement-derived values. For the tickers in the Evidence section,
FIFO-only matches the `positions.realized_pnl_cents` values in `data/kalshi.db`, while the settlement-derived
component adds an extra (incorrect) loss term, so the sum is wildly wrong.

1. **FIFO Trade P&L** (from `_get_closed_trade_pnls_fifo`):
   - Tracks closes from fills history (handles cross-side closing via normalization)
   - Correctly calculates: bought at X, sold at Y, P&L = Y - X

2. **Settlement P&L** (from settlement loop):
   - Computes a value from settlement record fields:
     `revenue - yes_total_cost - no_total_cost - fees`
   - For the observed settlement rows in `data/kalshi.db`, `revenue` is 0 and both
     `yes_total_cost` and `no_total_cost` are non-zero, so this term becomes a large negative number.

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

In our DB, `PortfolioSettlement.yes_total_cost/no_total_cost` match the summed `trades.total_cost_cents` grouped by
`side` (and `yes_count/no_count` match the summed `trades.quantity`), even when the user had no settlement payout
(`revenue = 0`). That strongly suggests we cannot treat `yes_total_cost/no_total_cost` as “extra costs to subtract”
on top of FIFO P&L — it double counts the same history in an incompatible way.

---

## Database Evidence

**portfolio_settlements table:**
```text
SOMA: yes_total_cost=9708, no_total_cost=15134, revenue=0
CRED: yes_total_cost=9652, no_total_cost=16555, revenue=0
```

**trades table:**
- Buy YES trades: ~$193.60 total
- Sell NO trades: ~$316.89 total (but this is misleading - see normalization)

**Verified on this DB:** for these tickers, settlement totals match trade totals by side:

- `PortfolioSettlement.yes_total_cost == SUM(trades.total_cost_cents WHERE side='yes')`
- `PortfolioSettlement.no_total_cost == SUM(trades.total_cost_cents WHERE side='no')`
- `PortfolioSettlement.yes_count == SUM(trades.quantity WHERE side='yes')`
- `PortfolioSettlement.no_count == SUM(trades.quantity WHERE side='no')`

This means the settlement-derived term is *not independent* of fills history in our current dataset.

---

## Proposed Fix

### Correct direction (SSOT-driven)

- Treat FIFO (fills) as the canonical realized P&L source for markets that were closed via trading.
- Use `/portfolio/settlements` as the “forced close” event for positions that reach settlement without a corresponding
  closing trade in fills history.
- Do **not** add settlement-derived P&L for tickers whose positions are already fully closed by fills.

### Fix implemented

In `PnLCalculator.calculate_summary_with_trades`, settlement-derived P&L is now included only when it is needed to
complete history:

- If a ticker has no trades, settlement records can contribute realized P&L (existing behavior).
- If a ticker has trades but FIFO leaves open lots, settlement records can contribute realized P&L (to close remaining
  lots without a fill record).
- If a ticker has trades and FIFO closes all lots, settlement records for that ticker are skipped to avoid double
  counting.

Unit tests added to lock this in:
- `tests/unit/portfolio/test_pnl.py::TestPnLCalculatorSummary.test_summary_includes_settlement_pnl_when_open_lots_remain`
- `tests/unit/portfolio/test_pnl.py::TestPnLCalculatorSummary.test_summary_does_not_double_count_settlement_when_trades_closed`

---

## Verification Steps

1. Reproduce the fixed output:
   - `uv run kalshi portfolio pnl`
   - `uv run kalshi portfolio pnl -t KXTRUMPMENTION-26JAN15-SOMA`
   - `uv run kalshi portfolio pnl -t KXTRUMPMENTION-26JAN15-CRED`

2. Compute FIFO-only realized P&L (expected on this DB):
   - Per-ticker:
     ```bash
     uv run python - <<'PY'
     import asyncio
     from pathlib import Path

     from sqlalchemy import select

     from kalshi_research.cli.db import open_db
     from kalshi_research.portfolio.pnl import PnLCalculator
     from kalshi_research.portfolio.models import Trade

     async def main() -> None:
         calc = PnLCalculator()
         async with open_db(Path("data/kalshi.db")) as db, db.session_factory() as session:
             for ticker in (
                 "KXTRUMPMENTION-26JAN15-SOMA",
                 "KXTRUMPMENTION-26JAN15-CRED",
             ):
                 trades = list(
                     (await session.execute(select(Trade).where(Trade.ticker == ticker))).scalars()
                 )
                 print(ticker, calc.calculate_realized(trades))

     asyncio.run(main())
     PY
     ```
   - Expected totals on this DB:
     - FIFO-only realized: **-$174.43**
     - CLI realized (after fix): **-$174.43**

---

## Related Issues

- BUG-060 (Closed): "Duplicate realized P&L computation (ignores Kalshi's value)" - may be related
- BUG-057: "Portfolio P&L integrity (FIFO realized P&L + unknown handling)" - was thought to be fixed

---

## Test Coverage Needed

✅ Added:
1. Settlements are NOT double-counted when FIFO closed the ticker
2. Settlement P&L is included when trades leave open lots

---

## Affected Commands

- `kalshi portfolio pnl` - Shows inflated losses
- `kalshi portfolio pnl -t TICKER` - Shows inflated losses per ticker

---

## Workaround

No workaround needed after the fix. For older commits (pre-`41d0c3a`), treat realized P&L from `kalshi portfolio pnl` as
unreliable and use FIFO-only calculations (or Kalshi’s UI) as a sanity check.
