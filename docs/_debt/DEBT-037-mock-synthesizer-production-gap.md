# DEBT-037: MockSynthesizer in Production Path

**Status:** Active
**Priority:** P1 (High - Blocks entire agent system value proposition)
**Created:** 2026-01-18
**Component:** `kalshi_research.agent.providers.llm`, `kalshi_research.cli.agent`

---

## Summary

The `kalshi agent analyze` command uses `MockSynthesizer` unconditionally, which returns a trivial "+5% from market" prediction. This makes the entire agent analysis workflow **useless** until a real LLM synthesizer is implemented.

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

```python
# src/kalshi_research/cli/agent.py:262-268
# Create synthesizer (mock for Phase 1)
if human or not output_json:
    console.print(
        "[yellow]Warning:[/yellow] Using MockSynthesizer (Phase 1). "
        "Results are placeholder."
    )
synthesizer = MockSynthesizer()  # ALWAYS mock, no configuration
```

And:

```python
# src/kalshi_research/agent/providers/llm.py:77-79
# Simple mock: predict market price + 5% with low confidence
market_pct = int(input.snapshot.midpoint_prob * 100)
predicted = min(100, max(0, market_pct + 5))
```

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

## Recommended Fix

### Immediate (P1 - Do First)

1. Add warning to JSON mode output (add `"warning": "MockSynthesizer active"` to JSON)
2. Update docs to clearly state analyze is non-functional until Phase 2

### Phase 2 Implementation

See [SPEC-042](../_specs/SPEC-042-llm-synthesizer-implementation.md) for the implementation plan:
- Implement `ClaudeSynthesizer` (Anthropic) or another real backend
- Add `KALSHI_SYNTHESIZER_BACKEND` env var
- Factory function to select based on config

## Files Affected

- `src/kalshi_research/agent/providers/llm.py` - Add real implementations
- `src/kalshi_research/cli/agent.py` - Backend selection + JSON warning

## Acceptance Criteria

- [ ] JSON mode includes warning field when mock is active
- [ ] At least one real LLM synthesizer implemented (SPEC-042)
- [ ] Environment variable to select synthesizer backend
- [ ] Documentation clearly states Phase 1 limitation

## Related

- [SPEC-042: LLM Synthesizer Implementation](../_specs/SPEC-042-llm-synthesizer-implementation.md)
- [FUTURE-007: LLM Synthesizer Implementation (Archived)](../_archive/future/FUTURE-007-llm-synthesizer-implementation.md)
- [SPEC-032: Agent System Orchestration](../_specs/SPEC-032-agent-system-orchestration.md)
