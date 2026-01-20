# DEBT-038: Orchestrator Escalation Logic Not Implemented

**Status:** ✅ Resolved (2026-01-19)
**Priority:** P2 (Medium - Feature gap in agent system)
**Created:** 2026-01-19
**Resolution:** Option B - Remove escalation plumbing (YAGNI)

---

## Problem

The agent orchestrator carried an **escalation API surface** (`enable_escalation`, CLI flags) but escalation was
never implemented. This created a misleading “Phase 2” hook that did nothing.

Previous behavior (removed):

```python
escalated = False
if self.enable_escalation and verification.suggested_escalation:
    pass
```

The verifier can still set `VerificationReport.suggested_escalation`, but it is informational only.

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
**CHOSEN.**

1. Remove `enable_escalation` parameter from `AgentKernel`
2. Remove escalation CLI plumbing (`--no-escalation`)
3. Remove dead escalation code path
4. Keep `suggested_escalation` as informational only (logged, not acted on)
5. Update SPEC-032 to reflect escalation is deferred

---

## Implementation Notes

Changes implemented:
- `src/kalshi_research/agent/orchestrator.py`: removed escalation parameter/path; logs `suggested_escalation`.
- `src/kalshi_research/cli/agent.py`: removed `--no-escalation` flag.
- `docs/_archive/specs/SPEC-032-agent-system-orchestration.md`: escalation explicitly deferred.

---

## Acceptance Criteria

- [x] Escalation plumbing removed (YAGNI)
- [x] No dead-code escalation paths in production
- [x] `suggested_escalation` remains informational only
- [x] Unit tests updated for new API surface

---

## References

- [SPEC-032: Agent System Orchestration](../_archive/specs/SPEC-032-agent-system-orchestration.md)
- `src/kalshi_research/agent/orchestrator.py:122-127`
- `src/kalshi_research/agent/verify.py` (sets `suggested_escalation`)
