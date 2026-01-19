# DEBT-041: SPEC-030 Has Unchecked Acceptance Criteria

**Status:** ✅ Resolved (2026-01-19)
**Priority:** P2 (Medium - Spec marked "implemented" but items remain)
**Created:** 2026-01-19
**Resolution:** Option A - Add `--budget-usd` controls everywhere

---

## Problem

SPEC-030 (Exa Endpoint Strategy) is marked as "🟡 Phase 1 implemented" but has unchecked acceptance criteria:

```markdown
- [ ] Other Exa-powered commands have policy controls (Phase 2+; e.g. `news`, `research similar/deep`, thesis flows).
- [ ] citation verification logic (Phase 3)
```

This means:
1. Several Exa-powered commands lacked `--budget-usd` controls
2. Citation verification is not implemented

---

## Current State

### Commands WITH policy controls:
- `kalshi research context` - has `--mode` and `--budget-usd`
- `kalshi research topic` - has `--mode` and `--budget-usd`

### Commands updated to include budget controls (this resolution):
- `kalshi news collect`
- `kalshi research similar`
- `kalshi research deep`
- `kalshi research thesis create --with-research`
- `kalshi research thesis check-invalidation`
- `kalshi research thesis suggest`

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

## Resolution: Option A - Implement budget controls across all Exa commands

**Reasoning:** Exa calls cost real money. Consistent, explicit `--budget-usd` controls reduce surprise costs and align
the CLI surface with SPEC-030’s cost-bounded design.

**Implementation:** Added budget flags and enforcement (stop-before-spend where possible) across all Exa-powered commands.

---

## Acceptance Criteria

- [x] All Exa-powered commands have consistent policy controls
- [x] SPEC-030 acceptance criteria updated to reflect current implementation
- [ ] Citation verification remains deferred (Phase 3)

---

## References

- [SPEC-030: Exa Endpoint Strategy](../_specs/SPEC-030-exa-endpoint-strategy.md)
- Lines 211, 217 (unchecked items)
