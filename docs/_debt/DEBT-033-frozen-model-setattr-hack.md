# DEBT-033: Frozen Pydantic Model object.__setattr__ Hack

**Status:** Active
**Priority:** P2 (Medium - Code smell, potential bugs)
**Created:** 2026-01-18
**Component:** `kalshi_research.agent.research_agent`

---

## Summary

`research_agent.py` uses `object.__setattr__()` to bypass Pydantic's frozen model protection, mutating an immutable object. This violates the immutability contract and can cause subtle bugs.

## Location

```python
# src/kalshi_research/agent/research_agent.py:467
object.__setattr__(result, "factors", factors)
```

## Problem

Pydantic frozen models (`ConfigDict(frozen=True)`) are immutable by design. Using `object.__setattr__()` to bypass this:

1. **Violates the contract** - Other code assumes immutability
2. **Breaks caching** - Frozen models can be hashable/cacheable
3. **Hidden mutation** - Hard to trace, causes subtle bugs
4. **Code smell** - Indicates schema design problem

## Root Cause

The `ResearchStepResult` schema likely doesn't have a `factors` field, but the code needs to attach factors after construction.

## Recommended Fix

Add `factors` field to the schema properly:

```python
# Before
class ResearchStepResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    # ... other fields

# After
class ResearchStepResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    factors: list[Factor] = Field(default_factory=list)
```

Then construct the model with factors included:

```python
# Before
result = ResearchStepResult(...)
object.__setattr__(result, "factors", factors)

# After
result = ResearchStepResult(..., factors=factors)
```

## Files Affected

- `src/kalshi_research/agent/research_agent.py`
- `src/kalshi_research/agent/schemas.py` (may need schema update)

## Acceptance Criteria

- [ ] No `object.__setattr__()` calls on Pydantic models
- [ ] Schema includes all required fields
- [ ] Tests pass without hack
