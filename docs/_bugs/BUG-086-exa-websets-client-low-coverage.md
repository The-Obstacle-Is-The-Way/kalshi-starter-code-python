# BUG-086: Exa Websets Client Low Test Coverage

**Status:** Active
**Priority:** P3 (Low - Feature not yet exposed via CLI)
**Created:** 2026-01-18
**Component:** `exa.websets`

---

## Summary

The Exa Websets client (`src/kalshi_research/exa/websets/client.py`) has 54% test coverage with 4 of 9 Phase 1 endpoints untested.

## Coverage Details

| File | Coverage |
|------|----------|
| `client.py` | **54%** |
| `models.py` | 88% |

## Untested Endpoints

Based on SPEC-038 Phase 1 endpoints:

| Endpoint | Tested |
|----------|--------|
| `create_webset()` | |
| `get_webset()` | |
| `list_websets()` | |
| `delete_webset()` | |
| `create_search()` | |
| `get_search()` | |
| `list_searches()` | |
| `cancel_search()` | |
| `get_search_items()` | |

## Verification Command

```bash
uv run pytest tests/unit/exa/websets/ --cov=kalshi_research.exa.websets --cov-report=term-missing
```

## Recommended Fix

Add tests in `tests/unit/exa/websets/test_client.py` for each endpoint:

```python
@respx.mock
async def test_create_webset():
    """Test webset creation."""
    respx.post("https://api.exa.ai/websets").mock(
        return_value=httpx.Response(200, json={...})
    )
    ...

@respx.mock
async def test_get_webset():
    """Test webset retrieval."""
    ...
```

## Acceptance Criteria

- [ ] All 9 Phase 1 endpoints have tests
- [ ] client.py coverage >= 80%
- [ ] Error paths tested (404, rate limit)
