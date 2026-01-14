# BUG-083: Position Sync Creates Duplicate Rows for Closed Positions

**Status:** Open
**Priority:** P2 (Medium - data integrity, not financial risk)
**Component:** `src/kalshi_research/portfolio/syncer.py`
**Found:** 2026-01-14
**Reporter:** Adversarial review during BUG-082 fix

---

## Summary

The portfolio syncer creates **duplicate position rows** for the same `(ticker, side)` combination when a position is closed and then re-synced. This causes data integrity issues but does NOT affect P&L calculations (which use FIFO from trades, not the positions table).

---

## Root Cause

In `syncer.py:127-130`, the sync logic only queries **open** positions to check for existing records:

```python
result = await session.execute(
    select(Position).where(Position.quantity > 0, Position.closed_at.is_(None))
)
existing_open = {p.ticker: p for p in result.scalars().all()}
```

When a position closes (`quantity=0, closed_at IS NOT NULL`), subsequent syncs:
1. Query for open positions - doesn't find the closed one
2. See the ticker in API response (Kalshi returns closed positions with `realized_pnl`)
3. Create a NEW row instead of updating the existing closed position

---

## Impact

### Current Database State

| Ticker | Duplicate Rows | All Closed? |
|--------|---------------|-------------|
| KXNCAAFSPREAD-26JAN09OREIND-IND3 | 3 | Yes (qty=0) |
| KXNFLAFCCHAMP-25-DEN | 3 | Yes (qty=0) |
| KXSB-26-DEN | 3 | Yes (qty=0) |

### P&L Impact: NONE

The P&L calculator uses **FIFO from trades**, not `positions.realized_pnl_cents`:

```python
# pnl.py uses trades, not positions:
fifo_result = self._get_closed_trade_pnls_fifo(trades)
```

So duplicate position rows do NOT cause incorrect P&L calculations.

### Data Integrity Impact: MEDIUM

1. **Incorrect row counts** - `SELECT COUNT(*) FROM positions` overcounts
2. **Confusing queries** - Joining on positions may return unexpected duplicates
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

### Option A: Query ALL positions (not just open)

```python
# Before (broken):
result = await session.execute(
    select(Position).where(Position.quantity > 0, Position.closed_at.is_(None))
)
existing_open = {p.ticker: p for p in result.scalars().all()}

# After (fixed):
result = await session.execute(select(Position))
existing_by_ticker = {p.ticker: p for p in result.scalars().all()}
```

**Pros:** Simple fix
**Cons:** Doesn't prevent duplicates if DB already has them

### Option B: Add UNIQUE constraint + upsert

```sql
-- Migration: add unique constraint
CREATE UNIQUE INDEX uq_positions_ticker_side ON positions(ticker, side);
```

Then use SQLAlchemy's `on_conflict_do_update`:

```python
from sqlalchemy.dialects.sqlite import insert

stmt = insert(Position).values(...)
stmt = stmt.on_conflict_do_update(
    index_elements=['ticker', 'side'],
    set_={
        'quantity': stmt.excluded.quantity,
        'realized_pnl_cents': stmt.excluded.realized_pnl_cents,
        ...
    }
)
```

**Pros:** Database-enforced uniqueness, future-proof
**Cons:** Requires migration + cleanup of existing duplicates

### Option C: Dedupe existing + Option A

1. Run a cleanup script to remove duplicate rows
2. Apply Option A fix to prevent future duplicates
3. Optionally add UNIQUE constraint after cleanup

---

## Data Cleanup Script

```python
# One-time cleanup to remove duplicate position rows
async def dedupe_positions(db: DatabaseManager):
    async with db.session_factory() as session, session.begin():
        # Find duplicates (keep the one with earliest opened_at)
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

- [ ] No duplicate `(ticker, side)` rows in positions table
- [ ] Subsequent syncs update existing rows (not create new ones)
- [ ] UNIQUE constraint or equivalent prevents future duplicates
- [ ] Cleanup script provided for existing data

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
