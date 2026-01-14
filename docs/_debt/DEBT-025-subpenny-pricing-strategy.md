# DEBT-025: Subpenny Pricing Strategy (FixedPointDollars → storage + rounding policy)

**Priority:** P2 (Pricing/P&L correctness; forward compatibility with Kalshi subpenny migration)
**Status:** 🟡 Partially Implemented
**Created:** 2026-01-14
**Related:** BUG-081, BUG-074, DEBT-014

---

## Summary

Kalshi is migrating from integer cent fields to fixed-point dollar strings (`*_dollars`) and explicitly warns that
systems must handle non-integer prices during the subpenny migration. Our codebase still assumes integer-cent prices at
multiple layers (models, DB snapshots, portfolio mark pricing).

This debt item tracks the **explicit policy decision** we should make for this repo:

- **Option A (recommended for our internal CLI):** round to nearest cent (half-up) and accept that subpenny precision is
  not represented.
- **Option B:** represent subpenny precisely (store fixed-point dollars or microcents everywhere).

---

## Current State (SSOT)

### Status Update (2026-01-14)

- ✅ Market + Orderbook dollar→cent conversion now shares a single helper and rounds half-up (BUG-081 fixed).
- ✅ Portfolio mark pricing rounds half-up for half-cent midpoints.
- 🔴 Remaining limitation: DB snapshots and many analytics still store integer cents (no sub-cent representation).

### 1) Market model conversion rounds-to-cent (lossy if subpenny is meaningful)

`Market.*_cents` converts `*_dollars` by rounding half-up to integer cents (shared helper). This matches `Orderbook`, but
still cannot preserve true sub-cent precision.

### 2) Orderbook conversion rounds half-up

`Orderbook` uses the same shared helper (half-up rounding + range validation) for dollar→cent conversion.

### 3) Persistence stores integer cents

`PriceSnapshot` stores `yes_bid/yes_ask/no_bid/no_ask` as integer cents, sourced from `Market.*_cents`.

This means any subpenny precision is discarded during ingestion, even if we fix rounding.

### 4) Portfolio mark pricing uses integer cents

`PortfolioSyncer.update_mark_prices()` stores `Position.current_price_cents` as an `int` and rounds half-up to the
nearest cent when computing midpoints. This cannot represent non-integer cents.

---

## Why This Matters (for our use case)

Even as an internal single-user CLI:

- Scanner rankings and thresholds can shift if subpenny prices are rounded to the nearest cent.
- Portfolio mark-to-market and unrealized P&L can change due to rounding (even when done consistently).
- If Kalshi starts returning meaningful subpenny increments, we risk “silent drift” in analytics.

---

## Recommended Policy (Option A)

For this repo’s current goals (internal research CLI, not a production service):

1. **Round-to-cent policy:** When a `*_dollars` value is not an exact cent, round half-up to the nearest cent.
2. **Single conversion SSOT:** Use one shared helper for dollar→cent conversion for both Market and Orderbook.
3. **Be explicit about limitations:** Document that we round to the nearest cent and do not preserve subpenny precision in
   DB snapshots or P&L.

This eliminates “silent truncation bias” and keeps internal consistency without a large refactor.

---

## Future Option (Option B) - Full Precision

If we later decide subpenny precision is materially important for research:

1. Store prices as `FixedPointDollars` strings (or integer microcents) in DB snapshots.
2. Convert internal calculations to use `Decimal` (avoid floats for money).
3. Update CLI formatting to display sub-cent values when present.
4. Add fixtures/tests covering subpenny markets using real API payloads.

This is a larger migration and should be treated as its own spec once requirements are clear.

---

## Next Actions

- Decide if true subpenny precision is materially important for our research workflows.
- If yes, write an implementation spec for Option B (DB + model precision migration).
