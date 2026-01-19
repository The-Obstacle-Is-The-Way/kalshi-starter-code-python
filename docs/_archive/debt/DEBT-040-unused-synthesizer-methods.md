# DEBT-040: Unused Synthesizer Cost/Token Tracking Methods

**Status:** ✅ Resolved (Removed dead cumulative tracking)
**Priority:** P3 (Low - Implemented but not wired)
**Created:** 2026-01-19
**Resolved:** 2026-01-19

---

> Archived: resolved by removing unused cumulative cost/token tracking methods.

## Problem (Historical)

The synthesizer classes implement cost and token tracking methods that are never called:

```python
# ClaudeSynthesizer, MockSynthesizer, BudgetedClaudeSynthesizer all have:
def get_total_cost_usd(self) -> float: ...
def get_total_tokens(self) -> int: ...
```

These are implemented but:
1. Never called from CLI
2. Never exposed to user
3. Never logged or tracked

The `get_last_call_cost_usd()` IS used (in `orchestrator.py`), but cumulative tracking was dead.

---

## Resolution

- Removed `get_total_cost_usd()` and `get_total_tokens()` from `SynthesisProvider` and implementations.
- Removed unused cumulative tracking state and updated unit tests.
- Kept `get_last_call_cost_usd()` (used by the orchestrator for per-call reporting).

---

## Options

### Option A: Wire Up Cost Tracking (Recommended)

The methods exist for a reason - expose them:

1. Add `--show-cost` flag to `kalshi agent analyze`
2. Print total tokens and USD spent at end of run
3. Store in `AgentRunResult` for JSON output

### Option B: Remove Dead Code

If we don't need cumulative tracking:
1. Remove `get_total_cost_usd()` and `get_total_tokens()`
2. Remove `_total_cost_usd` and `_total_tokens` instance variables
3. Keep only `get_last_call_cost_usd()` which IS used

### Option C: Keep for Future Use

Document that these are public API for programmatic use and not exposed via CLI yet.

---

## Acceptance Criteria

- [x] Methods either used OR removed
- [x] If kept, document why they exist
- [x] No vulture warnings for these methods

---

## References

- `src/kalshi_research/agent/providers/llm.py`
- Vulture audit output (60% confidence unused)
