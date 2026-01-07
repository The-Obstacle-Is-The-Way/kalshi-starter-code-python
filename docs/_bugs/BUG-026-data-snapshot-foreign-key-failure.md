# BUG-026: `kalshi data snapshot` FOREIGN KEY constraint failure (P0)

**Priority:** P0 (Blocks core data pipeline)
**Status:** 🟡 Open
**Found:** 2026-01-07
**Spec:** SPEC-003-data-layer-storage.md, SPEC-010-cli-completeness.md

---

## Summary

`kalshi data snapshot` crashes while inserting `price_snapshots` with:

- `sqlite3.IntegrityError: FOREIGN KEY constraint failed`

This prevents collecting any price history, which blocks analytics (metrics/correlation/calibration) and most of
the “data pipeline” workflows.

---

## Reproduction

1. `uv run kalshi data init --db /tmp/kalshi_audit.db`
2. `uv run kalshi data sync-markets --db /tmp/kalshi_audit.db --status open`
3. `uv run kalshi data snapshot --db /tmp/kalshi_audit.db --status open`

Observed failure (example ticker):

- `KXMVESPORTSMULTIGAMEEXTENDED-S2025473C9CD2E9A-30C474D2C9D`

Evidence:

- DB missing market row: `sqlite3 /tmp/kalshi_audit.db "select count(*) from markets where ticker='…';"` → `0`
- API market exists: `uv run kalshi market get KXMVESPORTSMULTIGAMEEXTENDED-S2025473C9CD2E9A-30C474D2C9D`

---

## Root Cause

- `price_snapshots.ticker` enforces a foreign key to `markets.ticker`.
- `DataFetcher.take_snapshot()` inserts snapshots for tickers returned by the live `/markets` API, but does not
  upsert the corresponding `markets` rows first.
- `kalshi data sync-markets` can be incomplete due to pagination caps (see BUG-027), so the snapshot fetch can
  encounter tickers not present in `markets`, triggering FK failure.

---

## Impact

- `kalshi data snapshot` unusable.
- `kalshi data collect` (continuous or `--once`) becomes unreliable.
- Downstream analysis commands relying on snapshots cannot function.

---

## Proposed Fix

- Make snapshot ingestion robust to missing `markets` rows:
  - Upsert minimal `Market` rows for any snapshot ticker before insert, **or**
  - Relax/remove the FK constraint (if the design allows “snapshot-first”), **or**
  - Change snapshot source to read tickers from the DB `markets` table (but only if sync is guaranteed complete).
- Also fix pagination truncation so `sync-markets` is not silently partial (BUG-027).

---

## Acceptance Criteria

- `uv run kalshi data snapshot --db <new_db>` completes without integrity errors.
- `uv run kalshi data collect --once --db <new_db>` completes and reports non-zero snapshots.
- `uv run kalshi analysis metrics <ticker> --db <new_db>` finds latest snapshot for a recently snapshotted market.

