# DEBT-036: Deep Research Timeout Hardcoded

**Status:** ✅ Resolved (Archived)
**Priority:** P3 (Low)
**Created:** 2026-01-18
**Closed:** 2026-01-19
**Component:** `agent.research_agent`

---

## Summary

This debt item is resolved. Deep research polling is configurable via `deep_research_timeout_seconds` and
`deep_research_poll_interval_seconds` and is covered by unit tests.

## Location

```python
# src/kalshi_research/agent/research_agent.py
# - build_plan(...) accepts deep_research_timeout_seconds / deep_research_poll_interval_seconds
# - _execute_research_task(...) reads timeout_seconds / poll_interval_seconds from step params
# - Exa client wait_for_research(...) receives poll_interval + timeout
```

## Problems

Resolved: timeout and poll interval are configurable and validated.

## Recommended Fix

No further action required for configurability. Optional future enhancement: exponential backoff on polling if API limits
become an issue.

## Files Affected

- `src/kalshi_research/agent/research_agent.py`
- `src/kalshi_research/cli/agent.py`

## Acceptance Criteria

✅ Timeout/poll interval configurable and validated; timeout error is explicit.
