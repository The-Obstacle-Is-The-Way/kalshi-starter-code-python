# BUG-017: Event Model Field Mismatch

## Priority
P1 (High) - Blocking Data Persistence

## Description
There is a critical mismatch between the Pydantic model used for API responses and the SQLAlchemy model used for database storage regarding the primary key field for Events.

- **API Model** (`src/kalshi_research/api/models/event.py`): Uses `event_ticker` as the identifier.
- **DB Model** (`src/kalshi_research/data/models.py`): Uses `ticker` as the primary key.

This impedance mismatch will cause failures when attempting to persist API `Event` objects directly into the database, or will require brittle manual mapping in every repository method.

## Location
- `src/kalshi_research/api/models/event.py`: Line 14
- `src/kalshi_research/data/models.py`: Line 28

## Impact
- **Data Loss:** Potential for data to be dropped if mapping isn't handled correctly.
- **Runtime Errors:** `AttributeError` when accessing the wrong field name.
- **Maintenance:** Increased complexity in the data access layer (DAL).

## Proposed Fix
1. Standardize on `ticker` as the canonical field name across both layers.
2. Update `src/kalshi_research/api/models/event.py` to use `ticker` or add a specific alias `event_ticker` mapping to `ticker`.
3. Ensure the `Event` Pydantic model can be directly converted to the SQLAlchemy model dictionary.
