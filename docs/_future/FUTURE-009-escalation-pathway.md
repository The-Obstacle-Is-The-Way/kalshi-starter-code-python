# FUTURE-009: Escalation Pathway (Centralized Multi-Agent Critique)

**Status:** Backlog (infrastructure exists, logic not implemented)
**Priority:** Medium
**Created:** 2026-01-19
**Blocked By:** Nothing (ready when needed)
**Owner:** Solo

---

## Summary

Implement the escalation pathway described in `docs/architecture/architecture-evolution-plan.md` (lines 233-258).

**What escalation means:** When the default single-agent synthesis produces low-confidence or failed verification results, escalate to deeper research and/or multi-agent critique to get a better answer.

**Current state:**
- `suggested_escalation` signal is computed in `verify.py`
- Escalation LOGIC is not implemented (was a stub, stub removed per DEBT-038)
- The pathway is designed, the wiring is not built

---

## Why This Exists

From the architecture evolution plan:

> Default: single orchestrator + deterministic feature extraction + strict validation.
> Escalation path (high-EV / low-confidence / contradictions): centralized multi-agent critique.

The system is designed to START cheap and ESCALATE when justified. This is cost-efficient and aligns with the arXiv research on agent scaling.

---

## What Escalation Would Do

When `verification.suggested_escalation == True`:

### Option A: Deeper Research (Simple)
```
1. Re-run Exa with mode=deep (instead of standard)
2. Re-synthesize with more evidence
3. Return improved result
```

### Option B: Model Upgrade (Medium)
```
1. Switch from Sonnet to Opus
2. Re-synthesize with stronger model
3. Return improved result
```

### Option C: Centralized Critics (Full)
```
1. Run ResearchCritic (challenge the evidence)
2. Run ConsistencyCritic (check for contradictions)
3. Run CalibrationCritic (check for base rate neglect)
4. Supervisor aggregates critiques
5. Re-synthesize with critic feedback
6. Return improved result
```

---

## Escalation Triggers (From Architecture Plan)

| Trigger | Description |
|---------|-------------|
| Verification failed | `VerificationReport.passed == False` |
| Low confidence | `AnalysisResult.confidence == "low"` |
| High EV opportunity | `abs(predicted_prob - market_prob) > threshold` AND sufficient liquidity |
| Missing citations | Medium/high confidence but few sources |
| Cross-market inconsistency | Arbitrage tool flags contradictions |

---

## Current Infrastructure

| Component | Status | Location |
|-----------|--------|----------|
| `suggested_escalation` signal | Computed | `agent/verify.py:99` |
| `VerificationReport` schema | Exists | `agent/schemas.py` |
| `AgentRunResult.escalated` field | Exists | `agent/schemas.py` |
| Escalation logic | NOT IMPLEMENTED | Was stub in `orchestrator.py`, removed |
| Critics (Research/Consistency/Calibration) | NOT IMPLEMENTED | Specced in architecture plan |
| `escalation.py` module | NOT IMPLEMENTED | Mentioned in SPEC-032 layout |

---

## Implementation Plan

### Phase 1: Simple Escalation (Re-research)
1. When `suggested_escalation == True`, re-run research with `mode=deep`
2. Re-synthesize with new evidence
3. Add `--escalation-budget-usd` CLI flag
4. Add `--no-escalation` to disable

### Phase 2: Model Upgrade Option
1. Add `--escalation-model` flag (default: same model, option: opus)
2. Track escalation costs separately

### Phase 3: Centralized Critics
1. Implement `agent/escalation.py` with critic functions
2. Add `ResearchCritic`, `ConsistencyCritic`, `CalibrationCritic`
3. Supervisor aggregation logic
4. Full cost tracking

---

## Cost Considerations

Escalation is expensive by design. The whole point is: "spend more money when it matters."

| Mode | Estimated Cost | When to Use |
|------|----------------|-------------|
| No escalation | $0.05-0.15 | Default, most markets |
| Re-research (deep) | +$0.50-1.00 | Low confidence, missing evidence |
| Model upgrade | +$0.50-2.00 | Verification failed |
| Full critics | +$2.00-5.00 | High EV opportunities only |

Budget ceilings are mandatory to prevent runaway costs.

---

## Acceptance Criteria

- [ ] Escalation triggers on `suggested_escalation == True`
- [ ] Re-runs research in `deep` mode
- [ ] Re-synthesizes with new evidence
- [ ] `--escalation-budget-usd` enforced
- [ ] `--no-escalation` disables entirely
- [ ] Escalation costs tracked in `AgentRunResult.total_cost_usd`
- [ ] Unit tests for escalation gating logic

---

## References

- `docs/architecture/architecture-evolution-plan.md` (lines 233-258)
- `docs/_specs/SPEC-032-agent-system-orchestration.md` (Phase 2)
- `docs/_archive/debt/DEBT-038-*` (stub removal rationale)
- [arXiv:2512.08296](https://arxiv.org/abs/2512.08296) - Scaling Agent Systems
- [arXiv:2512.20845](https://arxiv.org/abs/2512.20845) - Multi-Agent Reflection
