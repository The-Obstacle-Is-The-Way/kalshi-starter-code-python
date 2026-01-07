# BUG-025: Portfolio Positions Missing Cost Basis + Mark Price (P2)

**Priority:** P2 (High - portfolio accuracy)
**Status:** 🟡 Open
**Found:** 2026-01-07
**Spec:** SPEC-013-portfolio-sync-implementation.md

---

## Summary

Portfolio sync persists positions/trades, but position-level pricing fields remain unset:

- `avg_price_cents` is written as `0`
- `current_price_cents` / `unrealized_pnl_cents` remain `NULL`

This makes `kalshi portfolio positions` and unrealized P&L misleading.

---

## Root Cause

`PortfolioSyncer.sync_positions()` currently does not compute cost basis or mark-to-market pricing. The API payload does not provide a guaranteed “avg fill price” field, so cost basis must be computed from fills or derived from exposure fields.

---

## Impact

- Unrealized P&L cannot be computed reliably.
- Positions display shows `0¢` avg price and `-` current price, even after a successful sync.

---

## Proposed Fix

1. **Cost basis**
   - Compute `avg_price_cents` from synced fills (`Trade`) per `(ticker, side)` using FIFO or VWAP.
2. **Mark price**
   - Fetch current market mid price via public API for all open tickers in a single batch/pagination pass.
3. **Unrealized P&L**
   - Populate `current_price_cents` and `unrealized_pnl_cents` after mark price update.

---

## Acceptance Criteria

- `kalshi portfolio sync` populates cost basis and mark price for open positions.
- `kalshi portfolio positions` shows non-zero avg price when applicable.
- `kalshi portfolio pnl` includes accurate unrealized P&L for open positions.
