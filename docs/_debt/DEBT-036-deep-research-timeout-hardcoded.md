# DEBT-036: Deep Research Timeout Hardcoded

**Status:** Active
**Priority:** P3 (Low - Works but inflexible)
**Created:** 2026-01-18
**Component:** `agent.research_agent`

---

## Summary

The deep research polling loop has a hardcoded 5-minute timeout (60 polls × 5 seconds) with no configuration option and no exponential backoff.

## Location

```python
# src/kalshi_research/agent/research_agent.py:346-351
max_polls = 60
poll_count = 0
while task.status != ResearchStatus.COMPLETED and poll_count < max_polls:
    await asyncio.sleep(5)  # Wait 5 seconds between polls
    task = await self._exa.get_research_task(task.research_id)
    poll_count += 1
```

## Problems

1. **Not configurable** - Users can't adjust timeout for slow/fast research
2. **Fixed interval** - 5 seconds regardless of response time
3. **No exponential backoff** - Hammers API at fixed rate
4. **Silent timeout** - Returns partial result without clear indication

## Recommended Fix

1. **Add configuration**:
```python
def __init__(self, ..., deep_timeout_seconds: int = 300):
    self._deep_timeout = deep_timeout_seconds
```

2. **Add exponential backoff**:
```python
async def _poll_with_backoff(self, task_id: str) -> ResearchTask:
    delay = 2.0  # Start with 2 seconds
    max_delay = 30.0
    deadline = time.monotonic() + self._deep_timeout

    while time.monotonic() < deadline:
        task = await self._exa.get_research_task(task_id)
        if task.status == ResearchStatus.COMPLETED:
            return task
        await asyncio.sleep(delay)
        delay = min(delay * 1.5, max_delay)

    raise TimeoutError(f"Research task {task_id} timed out")
```

3. **Expose via CLI**:
```bash
kalshi agent research TICKER --deep-timeout 600
```

## Files Affected

- `src/kalshi_research/agent/research_agent.py`
- `src/kalshi_research/cli/agent.py` (add flag)

## Acceptance Criteria

- [ ] Timeout configurable via constructor/CLI
- [ ] Exponential backoff reduces API load
- [ ] Timeout error is explicit, not silent partial result
