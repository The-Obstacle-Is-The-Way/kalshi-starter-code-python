# DEBT-039: Broad Exception Catches Throughout Codebase

**Status:** Active
**Priority:** P3 (Low - Resilience vs. specificity tradeoff)
**Created:** 2026-01-19
**Audit Date:** 2026-01-19 (updated post-ralph-wiggum-loop cleanup)

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

### Execution (Safety-critical)
```text
src/kalshi_research/execution/executor.py:309, 333, 431
```

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
Review `executor.py:309, 331, 427` and determine if broad catches are appropriate for financial operations.

### Phase 2: Add exception logging (P3)
For each broad catch, ensure the exception type and message are logged, not just swallowed.

### Phase 3: Narrow where possible (P4)
Replace `except Exception` with specific exception types where the failure modes are known (e.g., `httpx.HTTPError`, `json.JSONDecodeError`).

---

## Rob C. Martin Principle

"Catch only what you can handle." If you can't handle ALL exceptions, don't catch them all. Let them propagate.

---

## Acceptance Criteria

- [ ] `executor.py` broad catches reviewed for safety
- [ ] All broad catches log the exception type (not just message)
- [ ] Obvious narrowing opportunities addressed (e.g., `httpx.HTTPError`)
- [ ] Document any broad catches that are intentionally kept

---

## References

- Previous audit: DEBT-034 (archived as "resolved" but these still exist)
- `grep -rn "except Exception" src/kalshi_research`
