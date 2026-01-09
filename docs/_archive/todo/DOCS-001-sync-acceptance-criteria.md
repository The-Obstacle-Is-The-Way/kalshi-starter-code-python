# DOCS-001: Sync Task Doc Acceptance Criteria

**Priority:** Medium
**Status:** Active
**Created:** 2026-01-09

---

## Problem

After completing multiple bug fixes, TODOs, and technical debt items in the Ralph Wiggum loop, the acceptance criteria checkboxes in the individual task docs may not accurately reflect completion status. This sync task ensures all task documentation matches the actual implementation state.

---

## Acceptance Criteria

- [x] All task docs in `docs/_bugs/` reviewed and acceptance criteria updated
  - BUG-048: All 6 criteria ✓
  - BUG-050: All 3 criteria ✓
  - BUG-049: Added 4 criteria, all ✓
  - BUG-047: Added 3 criteria, all ✓
- [x] All task docs in `docs/_debt/` reviewed and acceptance criteria updated
  - DEBT-002: Phase 1 complete, all 7 criteria ✓
  - DEBT-003: Complete ✓
  - DEBT-001: Added 10 criteria, all ✓
- [x] All task docs in `docs/_todo/` reviewed and acceptance criteria updated
  - TODO-007: 1 of 2 criteria ✓ (optional future work noted)
  - TODO-008: Phase 1 complete, 2 of 3 criteria ✓ (Phase 2 future work)
  - TODO-009: Updated to show 10 of 11 criteria ✓ (1 pending deadline)
  - TODO-005: All 3 sub-tasks (a, b, c) complete ✓
  - TODO-006: Added 9 criteria, all ✓
- [x] All checked items in PROGRESS.md have corresponding checked acceptance criteria in their task docs
- [x] Documentation-only change (no code modifications)

---

## Implementation

Review each task doc that is marked as complete `[x]` in PROGRESS.md and verify that ALL acceptance criteria in the corresponding task doc are also checked `[x]`.

Task docs to review based on PROGRESS.md Phase 1-6:

**Phase 1: Critical Bug Fixes**
- BUG-048: Fix negative liquidity validation
- BUG-050: Add logging to silent exception

**Phase 2: Safety-Critical Fixes**
- BUG-049: Add rate limiter to read operations
- TODO-007: Implement MarketStatusVerifier
- TODO-008: Add dry_run parameter

**Phase 3: API Deprecation**
- TODO-009: Migrate from cent fields to dollar fields

**Phase 4: Research Quality**
- TODO-005a: Display open_time/created_time in market get
- TODO-005b: Add temporal validation to research workflow
- TODO-005c: Add market timing warnings to GOTCHAS.md
- BUG-047: Investigate portfolio sync discrepancy

**Phase 5: Technical Debt**
- DEBT-002: Complete Phase 1 magic number comments
- DEBT-003: Add session.begin() transaction boundaries
- DEBT-001: Create Pydantic models for portfolio methods

**Phase 6: Session Friction**
- TODO-006: Implement remaining code fixes from friction audit

---

## Testing

No automated tests required (documentation-only).

Manual verification:
1. Read PROGRESS.md
2. For each `[x]` item, read corresponding task doc
3. Verify all acceptance criteria in task doc are `[x]`
4. Update any `[ ]` criteria that should be `[x]`

---

## Notes

This is purely a documentation sync task to ensure the A++ standard is maintained: every acceptance criterion in every task doc must accurately reflect completion status.
