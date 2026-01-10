# Technical Debt

This directory tracks **known debt** and **audit checklists** for the repository.

## Current Status

**0 active debt items.** (All known debt items resolved or archived unless listed below.)

No active debt items.

## Next ID Tracker

Use this ID for the next debt item:
**DEBT-013**

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

### Recently Resolved (2026-01-10)

| ID | Title | Status |
|---|---|---|
| **[DEBT-012](../_archive/debt/DEBT-012-exa-error-observability.md)** | Exa pipeline error observability (missing trace context) | ✅ Complete |
| **[DEBT-011](../_archive/debt/DEBT-011-unbounded-disk-growth-controls.md)** | Unbounded disk growth (DB snapshots, logs, caches) | ✅ Complete |
| **[DEBT-008](../_archive/debt/DEBT-008-dead-code-cleanup.md)** | Dead Code Cleanup (True Slop) | ✅ Complete |
| **[DEBT-010](../_archive/debt/DEBT-010-reduce-boilerplate.md)** | Reduce Boilerplate & Structural Bloat | ✅ Complete |
| **[DEBT-009](../_archive/debt/DEBT-009-finish-halfway-implementations.md)** | Finish Halfway Implementations | ✅ Complete |
| **[DEBT-007](../_archive/debt/DEBT-007-a-plus-engineering-robustness-delta.md)** | A+ Engineering Robustness Delta (Operational Hardening Gaps) | ✅ Complete |

---

## Debt Transitions (Historical)

None. All debt items resolved or elevated to specs.

| Item | Resolution | Date |
|------|------------|------|
| DEBT-004 | Implemented via [SPEC-027](../_archive/specs/SPEC-027-settlement-timestamp.md) | 2026-01-09 |
| DEBT-002 Phase 2-3 | Closed as "Won't Fix" (see `technical-debt.md`) | 2026-01-09 |
