# DEBT-034: Broad Exception Catches in Agent/Execution Code

**Status:** Active
**Priority:** P3 (Low - Reduces debuggability)
**Created:** 2026-01-18
**Component:** `agent`, `execution`

---

## Summary

Multiple files use bare `except Exception:` catches that swallow all errors, reducing debuggability and potentially hiding bugs.

## Locations

### research_agent.py
```python
# Line 233, 317
except Exception:
    # Error swallowed, partial result returned
```

### state.py
```python
# Lines 70, 96, 113
except Exception:
    # State recovery errors swallowed
```

### executor.py
```python
# Lines 300, 302, 321
except Exception:
    # Execution errors may be swallowed
```

## Problem

Broad exception catches:

1. **Hide bugs** - Unexpected exceptions silently ignored
2. **Reduce debuggability** - No stack trace, hard to diagnose
3. **Catch too much** - Catches KeyboardInterrupt, SystemExit, etc. (when not using `BaseException`)
4. **Silent failures** - User doesn't know something went wrong

## Recommended Fix

1. **Catch specific exceptions**:
```python
# Before
except Exception:
    return partial_result

# After
except (httpx.TimeoutException, ExaAPIError) as e:
    logger.warning("Research step failed: %s", e)
    return partial_result
```

2. **Log exceptions**:
```python
except SomeError as e:
    logger.exception("Unexpected error in %s", context)
    raise
```

3. **Consider re-raising for unexpected errors**:
```python
except KnownError:
    # Handle gracefully
except Exception:
    logger.exception("Unexpected error")
    raise  # Don't swallow
```

## Files Affected

- `src/kalshi_research/agent/research_agent.py`
- `src/kalshi_research/agent/state.py`
- `src/kalshi_research/execution/executor.py`

## Acceptance Criteria

- [ ] All `except Exception` catches either log or have documented justification
- [ ] Catch specific exception types where possible
- [ ] No silent failures for unexpected errors
