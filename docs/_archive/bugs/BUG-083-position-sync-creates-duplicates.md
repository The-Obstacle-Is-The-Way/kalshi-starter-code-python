# BUG-083: Position Sync Creates Duplicate Rows for Closed Positions

**Status:** ✅ Resolved (2026-01-14)
**Priority:** P2 (Medium - data integrity, not financial risk)
**Component:** `src/kalshi_research/portfolio/syncer.py`
**Found:** 2026-01-14
**Reporter:** Adversarial review during BUG-082 fix

---

## Summary

`GET /portfolio/positions` can include **closed markets** where `position = 0` (with `realized_pnl` populated). The
portfolio syncer was treating these as “positions to upsert”, but because `position=0` is neither YES nor NO, it led to
**phantom open rows** (`quantity=0 AND closed_at IS NULL`) and **duplicate rows** for the same ticker on repeated syncs.

This is a data-integrity/UX bug (confusing `portfolio positions` and any query filtering only `closed_at IS NULL`). It
does **not** affect realized P&L, which is computed from `/portfolio/fills` + `/portfolio/settlements` FIFO logic.

---

## Root Cause

In `src/kalshi_research/portfolio/syncer.py`, `sync_positions()` previously:

1. Queried only **open** rows (`quantity > 0 AND closed_at IS NULL`) to find existing positions.
2. Iterated over the API response and processed `position=0` rows the same as open positions.
3. Derived `side="no"` for `position=0` (`pos_data.position > 0` is false).
4. Inserted a new `Position` row because no open row existed for that ticker.

Because `position=0` tickers were also added to the “seen” set, the “mark missing positions closed” pass never corrected
these rows. Re-running sync kept inserting another `quantity=0, closed_at=NULL` row for the same ticker.

```python
result = await session.execute(
    select(Position).where(Position.quantity > 0, Position.closed_at.is_(None))
)
existing_open = {p.ticker: p for p in result.scalars().all()}
```

The key SSOT detail is that `/portfolio/positions` may include `position=0` rows (confirmed in production), so the syncer
must treat them as closed and avoid inserting “open” records for them.

---

## Impact

### Current Database State

| Ticker | Duplicate Rows | `quantity=0`? | `closed_at IS NULL`? |
|--------|----------------|---------------|----------------------|
| KXNCAAFSPREAD-26JAN09OREIND-IND3 | 3 | Yes | Yes |
| KXNFLAFCCHAMP-25-DEN | 3 | Yes | Yes |
| KXSB-26-DEN | 3 | Yes | Yes |

### P&L Impact: NONE

The P&L calculator uses **FIFO from trades**, not `positions.realized_pnl_cents`:

```python
# pnl.py uses trades, not positions:
fifo_result = self._get_closed_trade_pnls_fifo(trades)
```

So duplicate position rows do NOT cause incorrect P&L calculations.

### Data Integrity Impact: MEDIUM

1. **Incorrect row counts** - `SELECT COUNT(*) FROM positions` overcounts
2. **Confusing CLI output** - `kalshi portfolio positions` can show “open” positions with `Qty=0`
3. **Potential future bugs** - Any code that sums `realized_pnl_cents` directly would double-count

---

## Reproduction

```bash
# Show duplicate positions
sqlite3 data/kalshi.db "
SELECT ticker, side, COUNT(*) as rows
FROM positions
GROUP BY ticker, side
HAVING COUNT(*) > 1;
"

# Output:
# KXNCAAFSPREAD-26JAN09OREIND-IND3|no|3
# KXNFLAFCCHAMP-25-DEN|no|3
# KXSB-26-DEN|no|3
```

---

## Fix Options

### Option A: Ignore `position=0` rows (recommended for this CLI)

```python
# In sync_positions(), skip any API PortfolioPosition where position == 0.
# These represent closed markets and should not create "open" Position rows.
```

**Pros:** Prevents future duplicates; aligns with how the CLI uses `positions` (open-only).
**Cons:** Does not backfill historical closed positions for cold-start databases (acceptable).

### Option B: Repair invariants for existing bad rows (recommended in addition to A)

Mark any `closed_at IS NULL AND quantity = 0` rows as closed on sync, so they stop appearing as open.

**Pros:** Fixes user-facing confusion immediately with no destructive deletes.
**Cons:** Leaves historical duplicate rows (now closed) in the database unless you run a manual cleanup.

---

## Data Cleanup Script

```python
# One-time cleanup to remove duplicate position rows
async def dedupe_positions(db: DatabaseManager):
    async with db.session_factory() as session, session.begin():
        # Find duplicates (keep the one with lowest rowid as a stable tie-breaker)
        result = await session.execute(text("""
            DELETE FROM positions
            WHERE rowid NOT IN (
                SELECT MIN(rowid)
                FROM positions
                GROUP BY ticker, side
            )
        """))
        print(f"Deleted {result.rowcount} duplicate rows")
```

---

## Acceptance Criteria

- [ ] Subsequent syncs do **not** create new `positions` rows for `position=0` tickers
- [ ] No `positions` rows exist with `closed_at IS NULL AND quantity = 0`
- [ ] `kalshi portfolio positions` never shows `Qty=0` rows
- [ ] Cleanup guidance exists for historical duplicates (optional)

---

## Resolution

Fixed `PortfolioSyncer.sync_positions()` to:

- Treat `/portfolio/positions` entries with `position=0` as closed (skip insert/update)
- Repair historical bad rows by marking any `quantity=0 AND closed_at IS NULL` positions as closed during sync

After updating, run `uv run kalshi portfolio sync` once to apply the repair to your local database.

---

## Test Case

```python
def test_sync_closed_position_does_not_create_duplicate():
    """Re-syncing a closed position should update, not insert."""
    # Setup: Create a position, close it
    # Sync again
    # Assert: Still only 1 row for that ticker/side
```

---

## Related

- **BUG-053**: Data sync concurrency-safe (IntegrityError on upsert) - Similar pattern
- **syncer.py:125-190**: Position sync logic
