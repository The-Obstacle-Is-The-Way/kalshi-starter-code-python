# DEBT-038: Orchestrator Escalation Logic Not Implemented

**Status:** Active
**Priority:** P2 (Medium - Feature gap in agent system)
**Created:** 2026-01-19
**Location:** `src/kalshi_research/agent/orchestrator.py:122-127`

---

## Problem

The `AgentKernel.run()` method has a TODO comment for escalation logic that was never implemented:

```python
# Step 5: Escalation (Phase 2 - not implemented yet)
escalated = False
if self.enable_escalation and verification.suggested_escalation:
    # TODO: Implement escalation logic in Phase 2
    # For now, just mark that escalation was suggested but not executed
    pass
```

The `enable_escalation` parameter exists, `verification.suggested_escalation` is computed, but the actual escalation behavior is a no-op.

---

## What Escalation Should Do

Per SPEC-032 (Agent System Orchestration), escalation means:
1. When verification fails (low confidence, insufficient citations, etc.)
2. Re-run research with higher budget/deeper mode
3. Or flag for human review
4. Or use a more capable model

Currently: None of this happens. The code just sets `escalated = False` and continues.

---

## Options

### Option A: Implement Escalation (Recommended)

1. Define escalation triggers (which verification failures trigger escalation)
2. Implement re-research with `ExaMode.DEEP` when `suggested_escalation=True`
3. Add budget guard to prevent runaway costs
4. Track escalation in `AgentRunResult`

### Option B: Remove Escalation Feature

1. Remove `enable_escalation` parameter from `AgentKernel`
2. Remove `suggested_escalation` from `VerificationReport`
3. Remove dead code path
4. Update SPEC-032 to remove escalation references

### Option C: Keep as Explicit "Not Yet Implemented"

1. Raise `NotImplementedError` when `enable_escalation=True` and escalation is triggered
2. Document clearly that escalation is not available
3. Add to FUTURE backlog

---

## Acceptance Criteria

- [ ] Escalation logic either implemented OR explicitly removed/blocked
- [ ] No silent `pass` statements in production code paths
- [ ] SPEC-032 updated to reflect actual behavior
- [ ] Tests cover the chosen behavior

---

## References

- [SPEC-032: Agent System Orchestration](../_archive/specs/SPEC-032-agent-system-orchestration.md)
- `src/kalshi_research/agent/orchestrator.py:122-127`
- `src/kalshi_research/agent/verify.py` (sets `suggested_escalation`)
