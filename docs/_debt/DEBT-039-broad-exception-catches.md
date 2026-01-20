# DEBT-039: Broad Exception Catches Throughout Codebase

**Status:** Resolved
**Priority:** P3 (Low - Resilience vs. specificity tradeoff)
**Created:** 2026-01-19
**Audit Date:** 2026-01-20 (DEBT-039-B completed)

---

## Problem

The codebase has **48 instances** of `except Exception` or `except Exception as e` that catch all exceptions broadly. This can:
1. Hide bugs by catching unexpected errors
2. Make debugging harder
3. Violate the principle of catching only what you can handle

---

## Locations Found

### Research/Exa (External API resilience)
```text
src/kalshi_research/research/invalidation.py:90
src/kalshi_research/research/thesis_research.py:129, 175, 224
src/kalshi_research/research/context.py:215
src/kalshi_research/research/topic.py:72, 119
src/kalshi_research/research/notebook_utils.py:74
src/kalshi_research/exa/cache.py:75, 141
src/kalshi_research/agent/research_agent.py:253
```

### CLI (User-facing error handling)
```text
src/kalshi_research/cli/alerts.py:142
src/kalshi_research/cli/research.py:910 (and others)
src/kalshi_research/cli/market.py:68, 120, 178, 338, 542
src/kalshi_research/cli/__init__.py:105
src/kalshi_research/cli/scan.py:543, 843
src/kalshi_research/cli/data.py:142, 313
src/kalshi_research/cli/browse.py:33, 101, 167 (SPEC-043)
src/kalshi_research/cli/event.py:104, 257, 318, 382 (SPEC-043)
src/kalshi_research/cli/mve.py (multiple) (SPEC-043)
```

### Execution (Safety-critical) ✅ AUDITED 2026-01-20
```text
src/kalshi_research/execution/executor.py:319, 349, 522 (line numbers updated after refactoring)
```

**Audit Results (DEBT-039-A, 2026-01-20):**
1. `_check_orderbook_safety` (line 319): Narrowed to `(KalshiAPIError, httpx.HTTPError, httpx.TimeoutException)`. Fails closed (blocks trade). Logs exception type. ✅
2. `_check_liquidity_grade` (line 349): Narrowed to same exceptions. Fails closed. Logs exception type. ✅
3. `create_order` audit logging (line 522): **INTENTIONALLY BROAD** - This catch exists solely for audit logging; the exception is ALWAYS re-raised. Narrowing would miss unexpected failures in the audit trail. Safety analysis: No silent failure risk because the exception propagates.

**DEBT-039-B Changes (2026-01-20):**

Exception type logging added:
- `exa/cache.py:141` (clear_expired): Added `logger.debug()` with `exc_info=True`
- `research/invalidation.py:128`: Added `exc_info=True` to existing warning
- `research/thesis_research.py:313`: Added `exc_info=True` to existing error log
- `api/websocket/client.py:275`: Converted f-string log to structured log with `exc_info=True`

Narrowed exception types:
- `exa/cache.py:75` (get): Narrowed from `Exception` to `(json.JSONDecodeError, KeyError, ValueError, TypeError, OSError)`
- `exa/cache.py:141` (clear_expired): Narrowed from `Exception` to `(json.JSONDecodeError, KeyError, ValueError, OSError)`

Already using `exc_info=True` or `logger.exception()` (no changes needed):
- All CLI top-level catches (acceptable per analysis)
- `data/scheduler.py` (uses `logger.exception()`)
- `news/collector.py` (has `exc_info=True`)
- `cli/alerts.py` (has `exc_info=True`)
- `portfolio/syncer.py` (has `exc_info=True`)
- `research/context.py` (has `exc_info=True`)
- `research/thesis_research.py:85,107` (has `exc_info=True`)
- `research/topic.py` (has `exc_info=True`)
- `api/websocket/client.py:212,251,262` (uses `logger.exception()`)
- `agent/research_agent.py` (uses `logger.exception()`)

### Other
```text
src/kalshi_research/news/collector.py:86
src/kalshi_research/portfolio/syncer.py:473
src/kalshi_research/api/websocket/client.py:212
```

---

## Analysis by Category

### CLI Code (Acceptable)
CLI commands SHOULD catch broadly at the top level to provide user-friendly error messages instead of stack traces. These are mostly fine.

### Exa/Research Code (Review Needed)
External API calls can fail in many ways. Broad catches may be appropriate, but should:
- Log the specific exception type
- Re-raise if it's a programming error (e.g., `TypeError`, `AttributeError`)

### Execution Code (CRITICAL - Review Required)
`executor.py` catches broadly in order placement/cancellation. This is dangerous because:
- A bug could silently fail to cancel an order
- Financial operations should fail loudly

---

## Recommended Actions

### Phase 1: Audit execution code (P1)
Review `executor.py:309, 333, 431` and determine if broad catches are appropriate for financial operations.

### Phase 2: Add exception logging (P3)
For each broad catch, ensure the exception type and message are logged, not just swallowed.

### Phase 3: Narrow where possible (P4)
Replace `except Exception` with specific exception types where the failure modes are known (e.g., `httpx.HTTPError`, `json.JSONDecodeError`).

---

## Rob C. Martin Principle

"Catch only what you can handle." If you can't handle ALL exceptions, don't catch them all. Let them propagate.

---

## Acceptance Criteria

- [x] `executor.py` broad catches reviewed for safety (DEBT-039-A, 2026-01-20)
- [x] All broad catches log the exception type (not just message) (DEBT-039-B, 2026-01-20)
- [x] Obvious narrowing opportunities addressed (e.g., `httpx.HTTPError`) (DEBT-039-B, 2026-01-20)
- [x] Document any broad catches that are intentionally kept (see "Audit Results" above)

---

## References

- Previous audit: DEBT-034 (archived as "resolved" but these still exist)
- `grep -rn "except Exception" src/kalshi_research`
