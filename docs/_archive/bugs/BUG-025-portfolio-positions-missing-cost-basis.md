# BUG-025: Portfolio Positions Missing Cost Basis + Mark Price (P2)

**Priority:** P2 (High - portfolio accuracy)
**Status:** ✅ Fixed (2026-01-07)
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Spec:** SPEC-013-portfolio-sync-implementation.md
**Checklist Ref:** code-audit-checklist.md Section 11 (Incomplete Implementations)

---

## Summary

Portfolio sync persisted positions/trades, but position-level pricing fields remained unset:

- `avg_price_cents` was written as `0`
- `current_price_cents` / `unrealized_pnl_cents` remained `NULL`

This made `kalshi portfolio positions` and unrealized P&L misleading.

---

## Root Cause

`PortfolioSyncer.sync_positions()` did not compute cost basis or mark-to-market pricing. The Kalshi API payload does not provide a guaranteed "avg fill price" field, so cost basis must be computed from fills.

**Best Practice Violation:**
- [IRS FIFO Cost Basis](https://coinledger.io/blog/cryptocurrency-tax-calculations-fifo-and-lifo-costing-methods-explained) — FIFO is the IRS default method
- [Mark-to-Market PnL](https://help.margex.com/help-center/leverage-trading-guide/how-leverage-works/pnl-calculation) — Use mid price for mark, not last traded

---

## Impact

- Unrealized P&L could not be computed reliably.
- Positions display showed `0¢` avg price and `-` current price, even after a successful sync.

---

## Fix Applied

### 1. FIFO Cost Basis Calculator

Added `compute_fifo_cost_basis()` helper function in `src/kalshi_research/portfolio/syncer.py`:

```python
def compute_fifo_cost_basis(trades: list[Trade], side: str) -> int:
    """
    Compute average cost basis for a position using FIFO.

    FIFO (First-In-First-Out) is the IRS default method.
    """
    lots: deque[tuple[int, int]] = deque()

    for trade in trades:
        if trade.side != side:
            continue

        if trade.action == "buy":
            lots.append((trade.quantity, trade.price_cents))
        elif trade.action == "sell":
            # Pop FIFO from queue
            remaining = trade.quantity
            while remaining > 0 and lots:
                lot_qty, _ = lots[0]
                if lot_qty <= remaining:
                    lots.popleft()
                    remaining -= lot_qty
                else:
                    lots[0] = (lot_qty - remaining, lots[0][1])
                    remaining = 0

    # Compute weighted average of remaining lots
    if not lots:
        return 0
    total_qty = sum(qty for qty, _ in lots)
    total_cost = sum(qty * price for qty, price in lots)
    return total_cost // total_qty if total_qty > 0 else 0
```

### 2. sync_positions() Now Computes Cost Basis

Modified `sync_positions()` to query trades and compute cost basis:

```python
# Compute cost basis from trades using FIFO
trades_result = await session.execute(
    select(Trade)
    .where(Trade.ticker == ticker)
    .order_by(Trade.executed_at)
)
trades = list(trades_result.scalars().all())
avg_price_cents = compute_fifo_cost_basis(trades, side)
```

### 2.1 Fills Price Mapping Uses YES/NO Correctly

Kalshi `/portfolio/fills` returns both `yes_price` and `no_price`. NO-side fills must use `no_price` (or fallback to `100 - yes_price`) when persisting trades, otherwise NO cost basis + P&L will be wrong.

`src/kalshi_research/portfolio/syncer.py` now chooses the correct price based on `fill["side"]`.

### 3. New `update_mark_prices()` Method

Added method to fetch current market prices and compute unrealized P&L:

```python
async def update_mark_prices(self, public_client: KalshiPublicClient) -> int:
    """Fetch current market prices and update mark prices + unrealized P&L."""
    # Uses midpoint of bid/ask as mark price
    # Skips unpriced markets (0/0 or 0/100)
    # Computes unrealized P&L = (mark_price - avg_cost) * quantity
```

### 4. CLI Wiring

Updated `kalshi portfolio sync` command:

- Added `--skip-mark-prices` flag for faster sync
- Now shows progress: trades → positions → mark prices
- Calls `update_mark_prices()` after sync

---

## Acceptance Criteria

- [x] `kalshi portfolio sync` populates cost basis (FIFO) from trades
- [x] `kalshi portfolio sync` fetches mark prices and computes unrealized P&L
- [x] `kalshi portfolio positions` shows non-zero avg price when applicable
- [x] Unpriced markets (0/0, 0/100) are skipped gracefully
- [x] Persisted fills use side-correct prices (`no_price` for NO fills)
- [x] Unit tests for FIFO cost basis calculation
- [x] Unit tests for mark price update

---

## Test Plan

```python
def test_compute_fifo_cost_basis_fifo_sell() -> None:
    """Sells should consume FIFO lots."""
    trades = [
        _make_trade("yes", "buy", 10, 40),  # Lot 1: 10 @ 40
        _make_trade("yes", "buy", 10, 60),  # Lot 2: 10 @ 60
        _make_trade("yes", "sell", 10, 70),  # Sell 10 (consumes Lot 1)
    ]
    # Remaining: 10 @ 60
    assert compute_fifo_cost_basis(trades, "yes") == 60

async def test_update_mark_prices_computes_unrealized_pnl() -> None:
    """Mark prices should update and compute unrealized P&L."""
    # Position: 10 contracts @ 40¢ cost basis
    # Market: yes_bid=48, yes_ask=52 -> midpoint=50
    # Expected unrealized P&L = (50 - 40) * 10 = 100¢
    ...
```

---

## Regression Tests Added

- `tests/unit/portfolio/test_syncer.py::test_compute_fifo_cost_basis_*` (7 tests)
- `tests/unit/portfolio/test_syncer.py::test_update_mark_prices_*` (3 tests)
- `tests/unit/portfolio/test_syncer.py::test_sync_trades_uses_no_price_for_no_side`

---

## Sources

- [IRS FIFO Cost Basis Methods](https://coinledger.io/blog/cryptocurrency-tax-calculations-fifo-and-lifo-costing-methods-explained)
- [Kalshi API Portfolio Docs](https://docs.kalshi.com/api-reference/portfolio/get-positions)
- [Mark-to-Market PnL Calculation](https://help.margex.com/help-center/leverage-trading-guide/how-leverage-works/pnl-calculation)
