# DEBT-003: Loose Database Transaction Management

## Overview
The application relies heavily on `async with session:` (connection management) but lacks consistent explicit transaction boundaries (`async with session.begin():`).

## Severity: Medium (Data Integrity)
- **Impact**: If a complex operation involves multiple writes (e.g., "save market" AND "save price snapshot"), and the second one fails, the first one might still be committed (autocommit behavior) or left in an undefined state depending on the driver.
- **Risk**: Partial data writes leading to corrupted state (e.g., a Market exists but its initial snapshot is missing).

## Pattern to Fix
**Current (Risky):**
```python
async with self.db.get_session() as session:
    session.add(market)
    await session.commit()  # Manual commit
```

**Recommended (Safe):**
```python
async with self.db.get_session() as session:
    async with session.begin():  # Auto-commit/rollback scope
        session.add(market)
```

## Locations
- `src/kalshi_research/data/repositories/base.py`
- `src/kalshi_research/portfolio/syncer.py`
