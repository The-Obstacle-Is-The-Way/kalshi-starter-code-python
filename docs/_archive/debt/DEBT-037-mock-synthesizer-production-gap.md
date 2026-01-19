# DEBT-037: MockSynthesizer in Production Path

**Status:** ✅ Archived (Resolved by SPEC-042)
**Priority:** P1 (Historical)
**Created:** 2026-01-18
**Component:** `kalshi_research.agent.providers.llm`, `kalshi_research.cli.agent`

---

## Summary

The `kalshi agent analyze` command originally used `MockSynthesizer` unconditionally, which returned a trivial "+5% from market" prediction. This made the agent analysis workflow **useless** until a real LLM synthesizer was implemented.

**This is not a bug but a spec design flaw:** SPEC-032 acceptance criteria never required real LLM predictions, only valid JSON output and schema compliance.

## Root Cause: Spec Design Flaw

SPEC-032 (lines 337-345) explicitly stated:
```
### Phase 1 (single orchestrator + rules verifier)
...
4. Add unit tests:
   - orchestrator behavior with stubbed providers
```

The acceptance criteria tested:
- Valid JSON output (MockSynthesizer satisfies this)
- Schema validation (MockSynthesizer satisfies this)
- Verification logic (works regardless of synthesizer)

The acceptance criteria did NOT require:
- "Real LLM returns meaningful predictions"
- "Synthesizer reasons about research data"

## Location

This was resolved by implementing SPEC-042:
- `ClaudeSynthesizer` (Anthropic) added with tool-based structured outputs.
- `get_synthesizer()` factory added; backend controlled via `KALSHI_SYNTHESIZER_BACKEND`.
- CLI now uses the factory and emits a warning in JSON output when mock is active.

## Problems

1. **analyze command output is meaningless** - Always returns market + 5%
2. **Warning only in human mode** - JSON mode gets no warning, silently returns garbage
3. **No LLM configuration** - MockSynthesizer is hardcoded, no way to switch
4. **Research data is ignored** - Exa costs money, but results are thrown away

## Impact

| Severity | Description |
|----------|-------------|
| **P1** | Entire agent system value blocked |
| **Cost** | Users pay Exa API costs for research that gets discarded |
| **UX** | JSON mode silently returns garbage with no indication |

## Resolution

This item is resolved by [SPEC-042](../_specs/SPEC-042-llm-synthesizer-implementation.md).

## Files Affected

- `src/kalshi_research/agent/providers/llm.py` - Add real implementations
- `src/kalshi_research/cli/agent.py` - Backend selection + JSON warning

## Acceptance Criteria

- [x] JSON mode includes warning field when mock is active
- [x] At least one real LLM synthesizer implemented (SPEC-042)
- [x] Environment variable to select synthesizer backend
- [x] Documentation includes env var instructions (`.env.example`)

## Related

- [SPEC-042: LLM Synthesizer Implementation](../_specs/SPEC-042-llm-synthesizer-implementation.md)
- [FUTURE-007: LLM Synthesizer Implementation (Archived)](../_archive/future/FUTURE-007-llm-synthesizer-implementation.md)
- [SPEC-032: Agent System Orchestration](../_specs/SPEC-032-agent-system-orchestration.md)
