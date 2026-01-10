# Technical Debt

This directory tracks **known debt** and **audit checklists** for the repository.

## Current Status

**4 active debt items.** (DEBT-005 resolved; DEBT-004 elevated to SPEC-027; DEBT-002 closed as "Won't Fix")

- [DEBT-007: A+ Engineering Robustness Delta (Operational Hardening Gaps)](DEBT-007-a-plus-engineering-robustness-delta.md)
- [DEBT-008: Dead Code Cleanup (True Slop)](DEBT-008-dead-code-cleanup.md)
- [DEBT-009: Finish Halfway Implementations](DEBT-009-finish-halfway-implementations.md)
- [DEBT-010: Reduce Boilerplate & Structural Bloat](DEBT-010-reduce-boilerplate.md)

## Next ID Tracker

Use this ID for the next debt item:
**DEBT-011**

---

## Files

- `docs/_debt/code-audit-checklist.md`: Periodic audit checklist / runbook (reference doc).
- `docs/_debt/technical-debt.md`: Living register of known debt (add new items here).
- `docs/_debt/security-audit.md`: Deep security audit findings (Agent Safety, Injection Risks).

## Workflow

- Add new debt as a short, actionable entry (priority + impact + fix path).
- Link to the relevant bug (`docs/_bugs/`) or task (`docs/_future/`) when applicable.
- When resolved, move the entry to the **Resolved** section (don't delete history).

---

## Archive (Resolved)

All resolved debt items are stored in
[`docs/_archive/debt/`](https://github.com/The-Obstacle-Is-The-Way/kalshi-starter-code-python/tree/main/docs/_archive/debt/).

### Recently Resolved (Ralph Wiggum Cleanup - 2026-01-09)

| ID | Title | Status |
|---|---|---|
| **DEBT-003** | Loose DB Transactions (session.begin() pattern) | ✅ Complete |
| **DEBT-002** | Magic Numbers Analysis (Phase 1 comments) | ✅ Complete |
| **DEBT-001** | API Client Typing (Pydantic models for portfolio) | ✅ Complete |

---

## Debt Transitions (Historical)

None. All debt items resolved or elevated to specs.

| Item | Resolution | Date |
|------|------------|------|
| DEBT-004 | Implemented via [SPEC-027](../_archive/specs/SPEC-027-settlement-timestamp.md) | 2026-01-09 |
| DEBT-002 Phase 2-3 | Closed as "Won't Fix" (see `technical-debt.md`) | 2026-01-09 |
