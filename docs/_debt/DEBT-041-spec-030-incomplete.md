# DEBT-041: SPEC-030 Has Unchecked Acceptance Criteria

**Status:** Active
**Priority:** P2 (Medium - Spec marked "implemented" but items remain)
**Created:** 2026-01-19

---

## Problem

SPEC-030 (Exa Endpoint Strategy) is marked as "🟡 Phase 1 implemented" but has unchecked acceptance criteria:

```markdown
- [ ] Other Exa-powered commands have policy controls (Phase 2+; e.g. `news`, `research similar/deep`, thesis flows).
- [ ] citation verification logic (Phase 3)
```

This means:
1. `kalshi news collect` has no budget controls
2. `kalshi research similar` has no budget controls
3. `kalshi research deep` has no budget controls (or does it?)
4. Thesis flows (`--with-research`) have no explicit budget controls
5. Citation verification is not implemented

---

## Current State

### Commands WITH policy controls:
- `kalshi research context` - has `--mode` and `--budget-usd`
- `kalshi research topic` - has `--mode` and `--budget-usd`

### Commands WITHOUT policy controls:
- `kalshi news collect` - no `--budget-usd`
- `kalshi research similar` - no `--budget-usd`
- `kalshi research deep` - unclear
- `kalshi research thesis create --with-research` - no `--budget-usd`
- `kalshi research thesis check-invalidation` - no `--budget-usd`
- `kalshi research thesis suggest` - no `--budget-usd`

---

## Options

### Option A: Implement Phase 2 Policy Controls

Add `--budget-usd` to all Exa-powered commands:
1. `news collect`
2. `research similar`
3. `research deep`
4. All thesis subcommands that use Exa

### Option B: Update Spec to Reflect Reality

If Phase 2 is intentionally deferred:
1. Create FUTURE item for Phase 2/3
2. Update SPEC-030 status to reflect only Phase 1 is complete
3. Archive SPEC-030 as "Phase 1 Complete"

### Option C: Mark Spec as Incomplete

Keep SPEC-030 active until all items are checked. Don't pretend it's implemented.

---

## Acceptance Criteria

- [ ] All Exa-powered commands have consistent policy controls OR
- [ ] SPEC-030 explicitly documents what's deferred and why
- [ ] No unchecked items in "implemented" specs

---

## References

- [SPEC-030: Exa Endpoint Strategy](../_specs/SPEC-030-exa-endpoint-strategy.md)
- Lines 211, 217 (unchecked items)
