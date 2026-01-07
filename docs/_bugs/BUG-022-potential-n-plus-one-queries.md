# BUG-022: Potential N+1 Query Performance Issues

## Priority
P3 (Medium) - Performance

## Description
The SQLAlchemy models and repositories do not appear to use eager loading (`joinedload`, `selectinload`) for related entities. Accessing relationships (like `market.event` or `event.markets`) inside a loop will trigger a separate SQL query for each item.

For example, iterating over 100 markets and accessing `market.event.ticker` will execute 101 SQL queries.

## Location
- `src/kalshi_research/data/models.py`: Relationship definitions.
- `src/kalshi_research/data/repositories/prices.py`: Bulk fetch methods.

## Impact
- **Latency:** Severe performance degradation when syncing or analyzing large datasets.
- **Database Load:** Unnecessary load on the SQLite database.

## Proposed Fix
1. Review all loops that access relationships.
2. Update repository methods to use `options(joinedload(Model.relationship))` when fetching data that will be accessed together.
3. Consider configuring relationships with `lazy="selectin"` for collections if appropriate.
