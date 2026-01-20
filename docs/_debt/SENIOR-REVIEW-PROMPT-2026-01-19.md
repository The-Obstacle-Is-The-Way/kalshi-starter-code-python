# Senior Review Prompt: Debt & Spec Resolution Plan

**Date:** 2026-01-19
**For:** Senior engineer review of resolution decisions
**Plan Location:** `docs/_debt/RESOLUTION-PLAN-2026-01-19.md`

---

## Your Task

You are a senior engineer reviewing a comprehensive resolution plan for 3 debt items and 3 specs in a Kalshi prediction market research CLI. The plan was created by a junior engineer (Claude Opus 4.5) and needs your approval or revision.

**Your job:**
1. Read the resolution plan critically
2. Validate or challenge each decision
3. Check for Rob C. Martin (Clean Code) violations
4. Check for Google DeepMind agent best practices alignment
5. Provide a final verdict: APPROVE, REVISE, or REJECT

---

## Context

### What is this project?
A **single-user CLI research platform** for a solo Kalshi prediction market trader. NOT a production web service. Key characteristics:
- Solo user (no multi-tenancy)
- Local deployment (SQLite, no uptime SLA)
- Pay-per-use APIs (Kalshi, Exa, Anthropic) - cost matters
- Real money at stake in prediction markets

### Files to Read

**Required reading:**
1. `docs/_debt/RESOLUTION-PLAN-2026-01-19.md` - The plan under review
2. `CLAUDE.md` - Project guidelines and philosophy

**Optional (for deep context):**
- `docs/_archive/debt/DEBT-038-orchestrator-escalation-not-implemented.md`
- `docs/_debt/DEBT-039-broad-exception-catches.md`
- `docs/_archive/debt/DEBT-041-spec-030-incomplete.md`
- `docs/_specs/SPEC-030-exa-endpoint-strategy.md`
- `docs/_specs/SPEC-034-trade-executor-safety-harness.md`
- `docs/_specs/SPEC-042-llm-synthesizer-implementation.md`

---

## Review Checklist

### 1. DEBT-038: Orchestrator Escalation
**Proposed Decision:** Option B - Remove escalation plumbing (YAGNI)

**Review questions:**
- [ ] Is removing escalation plumbing the right call for a single-user CLI (YAGNI)?
- [ ] Should `suggested_escalation` remain informational only?
- [ ] Is there any evidence escalation improves outcomes enough to justify cost/complexity?
- [ ] Does this align with YAGNI?

**Your verdict:** _____________________

---

### 2. DEBT-039: Broad Exception Catches
**Proposed Decision:** Option C - Risk-proportional narrowing (focus on executor.py)

**Review questions:**
- [ ] Is focusing on executor.py (financial operations) the right priority?
- [ ] Should CLI top-level catches be allowed to stay broad?
- [ ] Are we leaving too much technical debt in the research/Exa code?
- [ ] Is "log it but don't narrow" acceptable for P3 items?

**Your verdict:** _____________________

---

### 3. DEBT-041 / SPEC-030: Exa Budget Controls
**Proposed Decision:** Option A - Add `--budget-usd` controls to all Exa-powered commands

**Review questions:**
- [ ] Are budget flags implemented consistently across all Exa-powered commands?
- [ ] Do the commands stop before exceeding the budget where possible?
- [ ] Are warnings/UX clear when budgets are exhausted or exceeded?

**Your verdict:** _____________________

---

### 4. SPEC-034: TradeExecutor
**Proposed Decision:** Archive as "Phase 1 Complete"

**Review questions:**
- [ ] Is Phase 1 actually complete? (dry-run default, kill switch, audit logging)
- [ ] Is it okay that Phase 2 providers are "implemented" but not wired?
- [ ] Should we leave this active until there's a real trading use case?

**Your verdict:** _____________________

---

### 5. SPEC-042: LLM Synthesizer
**Proposed Decision:** Archive as "Phase 1 Complete"

**Review questions:**
- [ ] Does Claude Sonnet 4.5 actually work as expected?
- [ ] Is it okay that OpenAI/Gemini backends aren't implemented?
- [ ] Is the calibration layer (Phase 2) appropriately deferred?

**Your verdict:** _____________________

---

## Final Verdict Template

After your review, provide:

```markdown
## Senior Review Verdict

**Reviewer:** [Your name/model]
**Date:** 2026-01-19

### Overall Verdict: [APPROVE / APPROVE WITH CHANGES / REVISE / REJECT]

### Item-by-Item:

| Item | Decision | Verdict | Notes |
|------|----------|---------|-------|
| DEBT-038 | Remove escalation plumbing | ✅/⚠️/❌ | ___ |
| DEBT-039 | Risk-proportional | ✅/⚠️/❌ | ___ |
| DEBT-041 | Implement budget controls | ✅/⚠️/❌ | ___ |
| SPEC-034 | Archive Phase 1 | ✅/⚠️/❌ | ___ |
| SPEC-042 | Archive Phase 1 | ✅/⚠️/❌ | ___ |

### Required Changes (if any):
1. ___
2. ___

### Concerns (non-blocking):
1. ___

### Commendations:
1. ___
```

---

## Standards to Apply

### Rob C. Martin (Clean Code) Principles
- **YAGNI**: Don't build features until needed
- **Explicit > Implicit**: Silent failures are bad
- **Single Responsibility**: Each module does one thing
- **Catch only what you can handle**: Broad exceptions hide bugs

### Google DeepMind Agent Patterns
- **Cost-bounded**: APIs cost money; budget controls are features
- **Escalate on failure**: Use cheap first, escalate only when needed
- **Start simple**: Single agent before multi-agent complexity

### Project Philosophy (from CLAUDE.md)
- Single-user CLI, not a production service
- Avoid over-engineering
- Keep dependencies minimal
- Focus on correctness, UX, and robust error handling

---

## How to Run This Review

```bash
# Option 1: In Claude Code
# Paste this entire file as the first message

# Option 2: In a fresh session
# 1. Open new Claude Code session
# 2. Read CLAUDE.md
# 3. Read docs/_debt/RESOLUTION-PLAN-2026-01-19.md
# 4. Paste the "Review Checklist" and "Final Verdict Template" sections
# 5. Provide your verdict
```

---

*Generated by Claude Opus 4.5 | 2026-01-19*
