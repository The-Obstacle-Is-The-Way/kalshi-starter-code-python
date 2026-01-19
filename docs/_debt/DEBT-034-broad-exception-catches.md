# DEBT-034: Broad Exception Catches in Agent/Execution Code

**Status:** Active
**Priority:** P3 (Low - Reduces debuggability)
**Created:** 2026-01-18
**Component:** `agent`, `execution`

---

## Summary

There are a few broad `except Exception` catches in the agent/execution code. Some are intentional (e.g., skipping optional
safety checks when a provider fails), but the documentation and line references in this debt item drifted.

## Locations

### research_agent.py
```python
# src/kalshi_research/agent/research_agent.py:253
except Exception:
    logger.exception(...)
    raise
```

### executor.py
```python
# src/kalshi_research/execution/executor.py:307, 330
except Exception as exc:
    # Provider failure: skip optional checks (fail-open by design)
    logger.warning(...)
    # continue

# src/kalshi_research/execution/executor.py:430
except Exception as exc:
    # Capture error for audit, then re-raise
    raise
```

## Problem

Broad exception catches:

1. **Can hide programmer errors** when used in “continue” paths
2. **Reduce debuggability** if logged without enough context (exception type/stack)
3. **Can change safety posture** (fail-open vs fail-closed) when provider errors occur

## Recommended Fix

1. **Prefer specific exceptions** when feasible (provider/network errors), especially in “continue” paths:
```python
# Before
except Exception:
    logger.warning("provider_failed")
    # continue

# After
except (OSError, httpx.HTTPError, ValueError) as exc:
    logger.warning("provider_failed", error=str(exc))
    # continue
```

2. **Use `logger.exception(...)`** (or equivalent) when swallowing errors and debugging would benefit from stack traces:
```python
except Exception:
    logger.exception("unexpected_error")
    raise
```

3. **Document intentional fail-open behavior** where appropriate (e.g., optional safety checks).

## Files Affected

- `src/kalshi_research/agent/research_agent.py`
- `src/kalshi_research/execution/executor.py`

## Acceptance Criteria

- [ ] All `except Exception` catches either log or have documented justification
- [ ] Catch specific exception types where possible
- [ ] No silent failures for unexpected errors
