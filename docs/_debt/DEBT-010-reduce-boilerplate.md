# DEBT-010: Reduce Boilerplate & Structural Bloat

**Status:** 🔴 Active
**Priority:** P3
**Owner:** TBD
**Created:** 2026-01-10
**Audit Source:** [`bloat.md`](bloat.md)

## Summary

The audit identified structural patterns that contribute to bloat and maintenance friction, specifically repeated database initialization boilerplate and potentially over-abstracted repository layers.

## Scope

### 1. Database Initialization Boilerplate
- **Problem:** 16 repetitions of `await db.create_tables()` scattered across `cli/portfolio.py`, `cli/news.py`, etc.
- **Pattern:**
  ```python
  async with get_db() as db:
      await db.create_tables()  # <--- Repeated everywhere
      async with db.session() as session:
          ...
  ```
- **Action:**
    - Implement a `@db_session` or `@with_db` decorator for Typer commands that handles:
        1. Context manager entry.
        2. Table creation (idempotent check).
        3. Session injection.
    - Refactor CLI commands to use this decorator.

### 2. Repository Layer Review
- **Problem:** `BaseRepository` provides generic CRUD that is often unused or bypassed.
- **Action:**
    - Review `src/kalshi_research/data/repositories/`.
    - If a repository method is just a 1-line wrapper around a SQLAlchemy select, consider inlining it into the service layer to remove the abstraction overhead.
    - Simplify `BaseRepository` to only contain methods actually shared/used by subclasses.

## Success Criteria

- 16 instances of `await db.create_tables()` removed/consolidated.
- Database access pattern is consistent across all CLI commands.
