# BUG-087: Search Repository FTS5 Path Low Coverage

**Status:** Active
**Priority:** P4 (Cosmetic - Feature works, tests incomplete)
**Created:** 2026-01-18
**Component:** `data.repositories.search`

---

## Summary

The search repository (`src/kalshi_research/data/repositories/search.py`) has 64% coverage with the FTS5 (full-text search) code path undertested.

## Coverage Details

| File | Coverage |
|------|----------|
| `search.py` | **64%** |

## Untested Code Paths

FTS5 virtual table operations (lines 125-197):
- FTS5 index creation
- FTS5 query syntax handling
- FTS5 ranking/scoring

## Verification Command

```bash
uv run pytest tests/unit/data/repositories/test_search.py --cov=kalshi_research.data.repositories.search --cov-report=term-missing
```

## Recommended Fix

Add FTS5-specific tests:

```python
# tests/unit/data/repositories/test_search.py

async def test_fts5_index_creation():
    """FTS5 virtual table created on init."""
    ...

async def test_fts5_phrase_query():
    """FTS5 handles phrase queries correctly."""
    ...

async def test_fts5_ranking():
    """Results ranked by relevance."""
    ...
```

## Acceptance Criteria

- [ ] search.py coverage >= 80%
- [ ] FTS5 code path explicitly tested
- [ ] Edge cases (empty query, special chars) tested
