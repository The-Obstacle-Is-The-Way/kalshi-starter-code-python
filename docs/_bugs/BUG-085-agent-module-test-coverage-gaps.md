# BUG-085: Agent Module Test Coverage Gaps

**Status:** Active
**Priority:** P3 (Low - Not blocking, but reduces confidence)
**Created:** 2026-01-18
**Component:** `agent`

---

## Summary

The agent module has 86% overall coverage, but `research_agent.py` is at 72% with important paths untested.

## Coverage Details

| File | Coverage | Gap |
|------|----------|-----|
| `orchestrator.py` | 91% | Minor |
| `research_agent.py` | **72%** | Major |
| `schemas.py` | 100% | None |
| `state.py` | 83% | Medium |
| `verify.py` | 94% | Minor |

## Untested Paths in research_agent.py

1. **Step execution failures** (lines ~230-240) - What happens when individual steps fail
2. **Timeout path** (lines ~346-360) - Deep research polling timeout behavior
3. **State corruption recovery** - Malformed JSON in state file
4. **Budget exhaustion mid-step** - Running out of budget during execution

## Verification Command

```bash
uv run pytest tests/unit/agent/ --cov=kalshi_research.agent --cov-report=term-missing
```

## Recommended Fix

Add tests for:

```python
# tests/unit/agent/test_research_agent.py

def test_step_failure_returns_partial_result():
    """When a step fails, should return partial results."""
    ...

def test_deep_research_timeout():
    """When polling times out, should return what we have."""
    ...

def test_corrupted_state_file_recovery():
    """Malformed state file should not crash, should start fresh."""
    ...
```

## Acceptance Criteria

- [ ] research_agent.py coverage >= 85%
- [ ] Timeout path has explicit test
- [ ] Failure paths have tests
