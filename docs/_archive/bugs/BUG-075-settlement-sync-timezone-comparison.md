# BUG-075: Settlement Sync Duplicate Detection Fails Due to Timezone Mismatch

**Priority:** P1 (Data integrity - causes IntegrityError on sync)
**Status:** ✅ Fixed
**Found:** 2026-01-13
**Verified:** 2026-01-13 - Reproduced via unit test simulation
**Fixed:** 2026-01-13
**Affected Code:** `PortfolioSyncer.sync_settlements()` in `src/kalshi_research/portfolio/syncer.py`

---

## Summary

`PortfolioSyncer.sync_settlements()` fails with `IntegrityError` on duplicate settlements because:

1. SQLite stores datetimes **without timezone info** (naive datetimes)
2. Python creates **timezone-aware** datetimes from API responses
3. Comparison `key in existing_keys` fails even for identical timestamps
4. Duplicate insert triggers `UniqueConstraint` violation

---

## Root Cause

### The Code (syncer.py:322-330)

```python
existing_keys_result = await session.execute(
    select(PortfolioSettlement.ticker, PortfolioSettlement.settled_at)
)
existing_keys = {(row[0], row[1]) for row in existing_keys_result.all()}

for settlement in settlements:
    settled_at = datetime.fromisoformat(settlement.settled_time.replace("Z", "+00:00"))
    key = (settlement.ticker, settled_at)
    if key in existing_keys:  # <-- FAILS due to tzinfo mismatch
        continue
```

### The Problem

```python
# From API (timezone-aware):
dt_in = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)

# From SQLite (naive):
dt_out = datetime(2026, 1, 10, 12, 0)  # tzinfo=None

# Comparison fails!
dt_in == dt_out  # False
```

### Verified via Test

```python
# SQLite roundtrip loses timezone info
engine = create_engine('sqlite:///:memory:')
# ... insert dt with tzinfo=utc
# ... read it back
dt_out.tzinfo  # None
dt_in == dt_out  # False!
```

### Database Evidence

```sql
sqlite> SELECT settled_at FROM portfolio_settlements LIMIT 1;
2026-01-10 04:50:31.435826  -- No timezone info stored
```

---

## Impact

- `kalshi portfolio sync` crashes with `IntegrityError` on the second run
- Settlements are inserted once but cannot be deduplicated on subsequent syncs
- Users see cryptic SQLAlchemy stack trace

---

## Symptoms

```
Traceback (most recent call last):
  ...
  File ".../sqlalchemy/engine/base.py:1967 in _exec_single_context"
  ...
sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) UNIQUE constraint failed:
portfolio_settlements.ticker, portfolio_settlements.settled_at
```

---

## Fix Options

### Option A: Normalize Incoming Datetimes (Recommended)

Strip timezone info when creating the key for comparison:

```python
settled_at = datetime.fromisoformat(settlement.settled_time.replace("Z", "+00:00"))
# Normalize to naive for comparison (SQLite stores naive)
settled_at_naive = settled_at.replace(tzinfo=None)
key = (settlement.ticker, settled_at_naive)
```

**Pros:** Minimal change, preserves existing data
**Cons:** Slightly counterintuitive

### Option B: Store Naive Datetimes

Convert to naive before storage:

```python
settled_at = datetime.fromisoformat(settlement.settled_time.replace("Z", "+00:00"))
# Store as naive UTC
settled_at_for_storage = settled_at.replace(tzinfo=None)
```

**Pros:** Database and Python types match
**Cons:** Loses timezone metadata

### Option C: Use aiosqlite Timezone Extension

Configure SQLite to preserve timezone info.

**Pros:** Most "correct"
**Cons:** Requires migration, complex setup

---

## Recommended Fix

Normalize timestamps to a single canonical representation before comparison.

**Implemented:** Normalize both existing DB timestamps and incoming API timestamps to UTC-aware
datetimes before set membership checks, and add each inserted key to the in-memory set to avoid
same-run duplicates.

---

## Test Plan

1. Create unit test with in-memory SQLite that:
   - Inserts a settlement
   - Reads it back
   - Verifies normalized comparison works
2. Integration test: Run `portfolio sync` twice, verify no crash

---

## Related

| Item | Relationship |
|------|--------------|
| `portfolio/syncer.py:sync_settlements()` | Affected code |
| `portfolio/models.py:PortfolioSettlement` | Model with unique constraint |
| BUG-053 | Similar concurrency-safe upsert issue (different root cause) |

---

## Effort Estimate

~30 minutes (code change + tests)
