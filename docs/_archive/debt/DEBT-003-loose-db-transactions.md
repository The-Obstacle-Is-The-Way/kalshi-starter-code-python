# DEBT-003: Loose Database Transaction Management

## Status: COMPLETED (2026-01-09)

Implementation complete. Core code uses `session.begin()` pattern. All tests pass.

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

## Implementation
Updated the following locations:
- `src/kalshi_research/portfolio/syncer.py` (3 methods)
- `src/kalshi_research/data/fetcher.py` (3 methods)
- `src/kalshi_research/news/tracker.py` (2 methods)
- `src/kalshi_research/news/collector.py` (1 location)
- `src/kalshi_research/cli/news.py` (1 location)
- `src/kalshi_research/cli/portfolio.py` (1 location)
- `src/kalshi_research/data/repositories/base.py` (already correct - uses flush())

## Test Fixes
Fixed test mock setup issues:
- `tests/unit/data/test_fetcher.py`: Updated mock_db fixture to properly mock session.begin() using MagicMock (not AsyncMock)
- `tests/unit/cli/test_portfolio.py`: Fixed session.begin() mocks in two tests
- `tests/unit/portfolio/test_syncer.py`: Fixed _mock_session_begin helper function

Key insight: `session.begin()` is called synchronously but returns an async context manager, so it must be a MagicMock (not AsyncMock) that returns an AsyncMock context manager.
