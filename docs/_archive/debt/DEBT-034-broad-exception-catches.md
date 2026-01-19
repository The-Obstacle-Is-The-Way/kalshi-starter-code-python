# DEBT-034: Broad Exception Catches in Agent/Execution Code

**Status:** ✅ Archived (Resolved)
**Priority:** P3 (Historical)
**Created:** 2026-01-18
**Component:** `agent`, `execution`

---

## Summary

There were a few broad `except Exception` catches in the agent/execution code. Some were intentional, but two of them
resulted in **fail-open** behavior during live trading safety checks when provider calls failed.

This item is resolved by making provider failures **fail-closed** in live mode, while keeping auditability and
debuggability (stack traces via `logger.exception(...)`).

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
# src/kalshi_research/execution/executor.py:_run_live_checks
except Exception as exc:
    # Provider failure: record failure + log stack trace (fail-closed for live safety)
    failures.append(...)
    logger.exception(...)

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

## Resolution

Implemented the following:

1. **TradeExecutor safety checks now fail closed** when a provider is configured but fails:
   - orderbook provider failures now add a failure code and block live order placement
   - liquidity grade check only runs when configured, and provider failures block live order placement
2. **Provider failures now log stack traces** via `logger.exception(...)` for debuggability.
3. **Removed the only `# type: ignore` in `TradeExecutor.cancel_order()`** by correcting the return type.

## Recommended Fix (Implemented)

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

- [x] All `except Exception` catches either log or have documented justification
- [x] Catch specific exception types where possible (provider protocols remain generic; failures are fail-closed + logged)
- [x] No silent failures for unexpected errors
