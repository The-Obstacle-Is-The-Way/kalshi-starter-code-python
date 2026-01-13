# DEBT-022: Exa Research Task Recovery (Missing `list_research_tasks()`)

**Priority:** P2 (Required before SPEC-033 Research Agent)
**Status:** Resolved ✅
**Created:** 2026-01-13
**Resolved:** 2026-01-13
**Related:** SPEC-033 (Exa Research Agent), SPEC-030 (Exa Endpoint Strategy)

---

## Summary

Our `ExaClient` implements `create_research_task()` and `get_research_task()` but NOT `list_research_tasks()`.

This creates a **single point of failure**: if the process crashes while waiting for a research task, the task ID is lost and you cannot retrieve the results (despite paying for them).

---

## Current State

### What We Have

```python
# Create a research task
task = await exa.create_research_task(instructions="Analyze X...")

# Poll until complete (blocks)
result = await exa.wait_for_research(task.research_id, timeout=300)
```

This works for synchronous, single-task workflows where nothing goes wrong.

### What We're Missing

```python
# List all research tasks (missing)
tasks = await exa.list_research_tasks(cursor=None, limit=10)
for task in tasks.data:
    cost_total = task.cost_dollars.total if task.cost_dollars else None
    print(f"{task.research_id}: {task.status} - ${cost_total}")
```

**Exa API Reference (SSOT: `docs/_vendor-docs/exa-api-reference.md`):**

> - **GET** `/research/v1` (list)
> - **POST** `/research/v1` (create)
> - **GET** `/research/v1/{researchId}` (get / stream)

---

## Why This Matters

### Failure Scenarios Without `list_research_tasks()`

| Scenario | Impact | With List |
|----------|--------|-----------|
| **Process crash during `wait_for_research()`** | Task ID in memory is lost. Research completes on Exa servers, you're billed, but can't retrieve results. | Query API: "What tasks did I create in last hour?" Recover the result. |
| **Network timeout during polling** | If retry logic fails, task ID may be lost | Can always re-query by listing |
| **Multi-task parallelism** | Must manually track N task IDs in code, DB, or file | Query API for "all my running tasks" |
| **Session interruption** | Start research Monday, get results Tuesday - must persist ID yourself | Just list tasks next session |
| **Cost auditing** | Must log costs ourselves after each task | API is source of truth for all historical costs |
| **Orphan detection** | Can't find tasks you started but forgot about | List shows all tasks with status/cost |

### SPEC-033 (Research Agent) Dependency

SPEC-033 proposes a research agent that:
- Executes multi-step Exa workflows
- Enforces budget limits
- Produces structured outputs

**Critical Gap:** The spec says "stop early when budget exceeded" but doesn't address crash recovery.

If the agent crashes mid-research:
1. The task continues running on Exa's servers
2. You get billed
3. You can't retrieve results
4. Budget tracking is now incorrect (you think you spent $X, but actually spent $X + orphaned task cost)

**Without `list_research_tasks()`, SPEC-033 cannot be robust.**

---

## Proposed Implementation

### 1. Add Pydantic Models

```python
# src/kalshi_research/exa/models/research.py

class ResearchTaskListResponse(BaseModel):
    """Response from GET /research/v1 (OpenAPI: ListResearchResponseDto)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    data: list[ResearchTask]
    has_more: bool = Field(alias="hasMore")
    next_cursor: str | None = Field(alias="nextCursor")
```

**Why `data` / `nextCursor`?** The live OpenAPI spec uses wrapper keys:
`{"data": [...], "hasMore": false, "nextCursor": null}`.

### 2. Add Client Method

```python
# src/kalshi_research/exa/client.py

async def list_research_tasks(
    self,
    *,
    cursor: str | None = None,
    limit: int = 10,
) -> ResearchTaskListResponse:
    """List research tasks with pagination."""
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor

    data = await self._request("GET", "/research/v1", params=params)
    return ResearchTaskListResponse.model_validate(data)
```

### 3. Add Recovery Helper

```python
async def find_recent_research_task(
    self,
    *,
    instructions_prefix: str | None = None,
    created_after: int | None = None,
    status: ResearchStatus | None = None,
) -> ResearchTask | None:
    """Find a recent research task matching criteria.

    Useful for crash recovery: find a task you started but lost the ID for.
    """
    tasks = await self.list_research_tasks(limit=50)

    for item in tasks.data:
        if instructions_prefix and not item.instructions.startswith(instructions_prefix):
            continue
        if created_after and item.created_at < created_after:
            continue
        if status and item.status != status:
            continue

        # Fetch full task details
        return await self.get_research_task(item.research_id)

    return None
```

### 4. Record Golden Fixture

Add to `scripts/record_exa_responses.py`:

```python
# List research tasks (may be empty array if no tasks exist yet)
list_response = await exa._request("GET", "/research/v1", params={"limit": 5})
save_golden(name="research_task_list", response=list_response, metadata={...})
```

### 5. Add Tests

```python
# tests/unit/exa/test_client.py

@pytest.mark.asyncio
@respx.mock
async def test_list_research_tasks_success() -> None:
    response_json = _load_golden_exa_fixture("research_task_list_response.json")
    respx.get("https://api.exa.ai/research/v1").mock(
        return_value=Response(200, json=response_json)
    )

    async with _client() as exa:
        result = await exa.list_research_tasks(limit=10)

    assert isinstance(result.items, list)
```

---

## Effort Estimate

| Component | Effort |
|-----------|--------|
| Pydantic models | 15 min |
| Client method | 15 min |
| Recovery helper | 30 min |
| Golden fixture recording | 15 min |
| Unit tests | 30 min |
| **Total** | **~2 hours** |

---

## Acceptance Criteria

- [x] `list_research_tasks()` method added to `ExaClient`
- [x] Pydantic response models for list endpoint
- [x] Golden fixture recorded for list response
- [x] Unit test with golden fixture
- [x] Recovery helper `find_recent_research_task()` for crash recovery
- [x] SPEC-033 updated to note crash recovery strategy

---

## Resolution

Implemented:
- `ExaClient.list_research_tasks()` and `ExaClient.find_recent_research_task()`
- `ResearchTaskListResponse` model + exports
- Golden fixture `tests/fixtures/golden/exa/research_task_list_response.json` recorded via `scripts/record_exa_responses.py`
- Unit coverage for list + recovery helper
- SPEC-033 updated with crash recovery requirement

## Why P2 (Not P3)

This is P2 because:

1. **Cost risk**: Orphaned tasks cost real money with no way to audit
2. **SPEC-033 blocker**: Research agent cannot be robust without crash recovery
3. **Low effort**: ~2 hours to implement properly
4. **No workaround**: Can't implement this in userland without the API method

If we shipped SPEC-033 without this, we'd have a research agent that:
- Loses work on crash
- Can't audit costs
- Has no recovery path

That's not Rob C. Martin quality.

---

## Cross-References

| Item | Relationship |
|------|--------------|
| SPEC-030 | Exa endpoint strategy (should mention recovery) |
| SPEC-033 | Research agent (depends on this for robustness) |
| SPEC-038 | Websets API (separate, unrelated) |
| `docs/_vendor-docs/exa-api-reference.md` | SSOT for endpoint specs |
