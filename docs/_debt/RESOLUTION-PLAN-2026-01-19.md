# Comprehensive Debt & Spec Resolution Plan

**Date:** 2026-01-19
**Status:** Updated After Senior Review (Partially Implemented)
**Author:** Claude (Opus 4.5)

---

## Executive Summary

This document provides opinionated resolutions for all 3 active debt items and 3 active specs, grounded in:
1. **First principles** for what we're building
2. **Industry best practices** from 2025/2026 research
3. **Rob C. Martin (Uncle Bob)** principles: YAGNI, explicit > implicit, catch what you can handle
4. **Google DeepMind patterns** for LLM agent systems: cost-bounded, escalate on failure

Each item has **3 options analyzed** with a **chosen resolution and reasoning**.

---

## First Principles: What Are We Building?

### The Product
A **single-user CLI research platform** for a solo Kalshi prediction market trader. Key characteristics:

| Attribute | Reality | Implication |
|-----------|---------|-------------|
| Users | 1 (solo trader) | No multi-tenancy, no auth system |
| Deployment | Local machine | No uptime SLA, no horizontal scaling |
| Data | SQLite + local cache | ACID guarantees, but single-writer |
| Cost model | Pay-per-use APIs (Kalshi, Exa, Anthropic) | Budget controls matter |
| Risk surface | Real money in prediction markets | Safety rails for execution |

### What We're NOT Building
- NOT a production web service
- NOT a multi-agent autonomous trading system
- NOT an enterprise platform with circuit breakers, Prometheus, DI frameworks

### Design Philosophy
1. **Simple over clever** - Prefer straightforward code over "enterprise patterns"
2. **Explicit over implicit** - If something isn't implemented, say so
3. **YAGNI** - Don't build features until they're needed
4. **Cost-aware** - APIs cost money; budget controls are features
5. **Safe by default** - Trading must be opt-in, never accidental

---

## Industry Research Summary

### LLM Agent Escalation Patterns (2025-2026)

**Key findings from [arXiv "Detect, Explain, Escalate"](https://arxiv.org/abs/2504.18839)**:
- Escalation should be **cost-bounded** - use cheap models first, escalate on failure
- [BudgetMLAgent research](https://www.emergentmind.com/topics/cost-efficient-llm-agent-deployment) shows 94% cost reduction with escalate-on-failure patterns
- **OpenAI's guidance**: Set limits on retries; escalate when limits are exceeded

**DeepMind-style principle**: Escalation is an **optimization**, not a core feature. Start with single-agent, add escalation only when measured improvement justifies cost.

### Python Exception Handling (2025)

**Key findings from [qodo.ai](https://www.qodo.ai/blog/6-best-practices-for-python-exception-handling/) and [Miguel Grinberg](https://blog.miguelgrinberg.com/post/the-ultimate-guide-to-error-handling-in-python)**:
- Broad `except Exception` is **bad practice** - hides bugs
- Catch **specific exceptions** you know how to handle
- Keep try blocks **small and scoped**
- **Log exceptions** in production code
- **Exception**: CLI top-level handlers are acceptable for user-friendly errors

### API Cost Budget Controls (2025)

**Key findings from [Skywork.ai](https://skywork.ai/blog/ai-api-cost-throughput-pricing-token-math-budgets-2025/)**:
- Budget controls: 50/80/100% spend alerts with automated actions
- Per-command budgets with explicit CLI flags is standard
- **Anthropic pattern**: Usage tiers + rate limits prevent runaway costs

---

## Item-by-Item Analysis

---

### DEBT-038: Orchestrator Escalation Not Implemented

**Location:** `src/kalshi_research/agent/orchestrator.py`

**Problem:** The `enable_escalation` parameter exists, `suggested_escalation` is computed, but the actual escalation code is `pass` - a no-op.

#### Option A: Implement Escalation Now
**Description:** Build full escalation logic - when verification fails, re-run research with `ExaMode.DEEP`, use more capable model, etc.

**Pros:**
- Feature becomes real
- Aligns with SPEC-032 vision

**Cons:**
- YAGNI violation - no evidence escalation is needed
- Adds complexity for unproven value
- Cost risk - could double/triple research costs
- No calibration data to know if escalation improves outcomes

**Rob C. Martin says:** "You ain't gonna need it"

#### Option B: Remove Escalation Plumbing (YAGNI)
**Description:** Delete `enable_escalation` parameter and CLI flags, remove dead escalation code, keep
`suggested_escalation` informational only (logged, not acted on).

**Pros:**
- Clean code, no dead paths
- No confusion about what's supported

**Cons:**
- Loses the “Phase 2” API surface (but it was non-functional)
- Requires updating SPEC-032 to clarify escalation is deferred

**Google DeepMind says:** Start simple; add escalation only when it measurably improves outcomes.

#### Option C: Make Escalation Fail Explicitly
**Description:** When `enable_escalation=True` and escalation is triggered, raise `NotImplementedError("Escalation not implemented. Use enable_escalation=False or implement SPEC-032 Phase 2")`.

**Pros:**
- Explicit > implicit - no silent failures
- Preserves API surface for future implementation
- Tests can verify behavior
- Honest about current state

**Cons:**
- Still has "unimplemented" code
- Users might hit the error

**Rob C. Martin says:** "Make the implicit explicit"

**DECISION: Option B - Remove Escalation Plumbing (YAGNI)**

**Reasoning:**
1. The `enable_escalation` surface was misleading and unused (dead feature flag).
2. Raising `NotImplementedError` mid-run is a UX footgun for a CLI.
3. Keep escalation as FUTURE work until there’s evidence it improves outcomes.
4. Preserve the informational signal (`suggested_escalation`) for later experiments.

**Implementation:**
```python
# Escalation (deferred; informational only)
escalated = False
if verification.suggested_escalation:
    logger.info("Escalation suggested (deferred)", ticker=ticker, issues=verification.issues)
```

---

### DEBT-039: Broad Exception Catches Throughout Codebase

**Problem:** ~30 instances of `except Exception` that could hide bugs.

#### Option A: Narrow All Exception Catches
**Description:** Replace every `except Exception` with specific exceptions (`httpx.HTTPError`, `json.JSONDecodeError`, etc.).

**Pros:**
- Best practice per all sources
- Won't hide bugs

**Cons:**
- Large refactor (30 locations)
- Some catches are intentionally broad (CLI top-level)
- Risk of introducing bugs during refactor

#### Option B: Keep All Catches, Add Logging
**Description:** Add `logger.exception()` to every broad catch but don't narrow them.

**Pros:**
- Minimal code changes
- At least we see what's caught

**Cons:**
- Still hides bugs
- Doesn't fix the root issue

#### Option C: Risk-Proportional Narrowing (CHOSEN)
**Description:** Apply different standards based on risk:

| Category | Risk | Action |
|----------|------|--------|
| CLI top-level | Low (user-facing) | Keep broad, ensure error message is printed |
| Exa/Research | Medium (external API) | Log exception type, re-raise programming errors |
| **Executor** | **HIGH (financial)** | **Narrow to specific exceptions** |

**Pros:**
- Proportional to actual risk
- Focuses effort where it matters (money)
- Pragmatic for single-user CLI

**Cons:**
- Inconsistent rules
- Requires judgment calls

**Rob C. Martin says:** "Catch only what you can handle"

**DECISION: Option C - Risk-Proportional Narrowing**

**Reasoning:**
1. CLI catches are acceptable - user doesn't want stack traces
2. Research code catching broadly is tolerable - worst case is research fails
3. **Executor code catching broadly is DANGEROUS** - a bug could silently fail to cancel an order, losing real money
4. Focus engineering effort where risk is highest

**Implementation Priority:**
1. **P1:** Review and narrow `executor.py:309, 331, 427` - these are financial operations
2. **P3:** Add `logger.exception()` to all other broad catches
3. **P4:** Opportunistically narrow when touching those files

---

### DEBT-041: SPEC-030 Has Unchecked Acceptance Criteria

**Problem:** SPEC-030 has unchecked Phase 2/3 items:
- `news`, `research similar/deep`, thesis flows lack `--budget-usd`
- Citation verification not implemented

#### Option A: Implement Phase 2/3 Now
**Description:** Add `--budget-usd` to all Exa-powered commands, implement citation verification.

**Pros:**
- Spec is truly "complete"
- Consistent budget controls everywhere

**Cons:**
- YAGNI - most commands aren't used frequently
- Large surface area
- `research context` and `research topic` are the main commands

#### Option B: Close DEBT-041 as "By Design"
**Description:** Treat Phase 2/3 as backlog and document the gap.

**Pros:**
- Honest about priorities
- `research context` and `research topic` (the main commands) have controls
- Defers work until needed

**Cons:**
- Some commands lack budget controls
- Must be careful not to run up costs

#### Option C: Move Phase 2/3 to FUTURE
**Description:** Create `FUTURE-009-exa-budget-phase2.md` and archive SPEC-030 as "Phase 1 Complete".

**Pros:**
- Clear separation of "done" vs "future"
- Spec is closed cleanly

**Cons:**
- More documentation overhead
- Same outcome as Option B

**DECISION: Option A - Implement budget controls everywhere**

**Reasoning:**
1. Exa calls incur real costs; cost controls are a first-class feature for this repo.
2. Users should not need to remember “which Exa commands are safe”.
3. Consistent CLI flags reduce surprise bills and align with SPEC-030’s intent.

**Implementation:**
1. Add `--budget-usd` (and `--mode` where appropriate) to all Exa-powered commands:
   - `kalshi news collect`
   - `kalshi research similar`
   - `kalshi research deep`
   - `kalshi research thesis create --with-research`
   - `kalshi research thesis check-invalidation`
   - `kalshi research thesis suggest`
2. Update SPEC-030 acceptance criteria to mark controls complete
3. Archive DEBT-041 as resolved

---

### SPEC-034: TradeExecutor Safety Harness

**Current State:** Phase 1 implemented (dry-run default, kill switch, audit logging). Phase 2 (concrete providers) requires actual trading need.

#### Final Disposition: Archive as "Phase 1 Complete"

**Reasoning:**
1. Phase 1 is fully implemented and tested
2. Phase 2 requires concrete implementations of `BudgetTracker`, `PositionProvider`
3. No `kalshi trade ...` CLI exists (intentionally - manual trading)
4. This is blocked on actual need, not missing work

**Action:** Archive to `docs/_archive/specs/SPEC-034-trade-executor-safety-harness.md` with status "Phase 1 Complete - Phase 2 deferred until trading automation is desired"

---

### SPEC-042: LLM Synthesizer Implementation

**Current State:** Phase 1 implemented (Claude Sonnet 4.5 works). Phase 2 (calibration layer, multi-provider) is future work.

#### Final Disposition: Archive as "Phase 1 Complete"

**Reasoning:**
1. Claude Sonnet 4.5 synthesizer works
2. `kalshi agent analyze` produces real LLM-powered predictions
3. OpenAI/Gemini backends are YAGNI - Claude is the frontier model
4. Calibration layer is Phase 2 (requires historical prediction data)

**Action:** Archive to `docs/_archive/specs/SPEC-042-llm-synthesizer-implementation.md` with status "Phase 1 Complete"

---

## Summary of Decisions

| Item | Decision | Action |
|------|----------|--------|
| **DEBT-038** | Option B: Remove Escalation Plumbing | Remove dead flag/path; keep suggestion informational |
| **DEBT-039** | Option C: Risk-Proportional | Narrow executor catches (P1), log others (P3) |
| **DEBT-041** | Option A: Implement Budget Controls | Add `--budget-usd` across Exa-powered commands |
| **SPEC-030** | Keep Active | Citation verification remains backlog |
| **SPEC-034** | Propose Archive | Phase 1 complete; Phase 2 deferred (not implemented here) |
| **SPEC-042** | Propose Archive | Phase 1 complete; Phase 2 deferred (not implemented here) |

---

## Implementation Checklist

### Immediate (This Session)
- [x] DEBT-038: Remove escalation plumbing (YAGNI)
- [x] DEBT-041: Add budget controls to all Exa-powered commands
- [x] SPEC-030: Update acceptance criteria for budget controls

### P1 (Next Session)
- [ ] DEBT-039: Review and narrow `executor.py:309, 331, 427`

### P3 (Opportunistic)
- [ ] DEBT-039: Add logging to remaining broad catches

---

## References

### Web Research (2025-2026)
- [arXiv: Detect, Explain, Escalate](https://arxiv.org/abs/2504.18839) - LLM dialogue breakdown management
- [OpenAI: Practical Guide to Building Agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)
- [qodo.ai: 6 Best Practices for Python Exception Handling](https://www.qodo.ai/blog/6-best-practices-for-python-exception-handling/)
- [Miguel Grinberg: Ultimate Guide to Error Handling in Python](https://blog.miguelgrinberg.com/post/the-ultimate-guide-to-error-handling-in-python)
- [Skywork.ai: AI API Cost & Throughput Management](https://skywork.ai/blog/ai-api-cost-throughput-pricing-token-math-budgets-2025/)
- [Anthropic API Pricing](https://www.finout.io/blog/anthropic-api-pricing)

### Internal
- [SPEC-030: Exa Endpoint Strategy](../_specs/SPEC-030-exa-endpoint-strategy.md)
- [SPEC-032: Agent System Orchestration](../_archive/specs/SPEC-032-agent-system-orchestration.md)
- [SPEC-034: TradeExecutor Safety Harness](../_specs/SPEC-034-trade-executor-safety-harness.md)
- [SPEC-042: LLM Synthesizer Implementation](../_specs/SPEC-042-llm-synthesizer-implementation.md)

---

## Senior Review Outcome (2026-01-19)

Senior review completed and applied:

1. **DEBT-038:** Remove escalation plumbing (YAGNI); keep `suggested_escalation` informational only.
2. **DEBT-041:** Implement `--budget-usd` controls across all Exa-powered commands.

Remaining open question:

- **DEBT-039:** Narrow broad exception catches in `executor.py` (financial-risk surface).

---

*Generated by Claude Opus 4.5 | 2026-01-19*
