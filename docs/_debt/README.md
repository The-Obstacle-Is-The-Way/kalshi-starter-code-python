# Technical Debt

This directory tracks **known debt** and **audit checklists** for the repository.

## Current Status

**5 active debt items.**

| ID | Title | Priority | Status |
|---|---|---|---|
| **[DEBT-018](DEBT-018-test-ssot-stabilization.md)** | Test SSOT Stabilization (Fixtures, Mocks, Exa Coverage) | **P1** | Open |
| **[DEBT-014](DEBT-014-friction-residuals.md)** | Friction Residuals - Research Pipeline & Agent Design | P1-P3 | Open (Needs Design) |
| **[DEBT-016](DEBT-016-fixture-drift-ci.md)** | Automate Fixture Drift Detection + Weekly Re-Recording | P2 | Open (Proposed) |
| **[DEBT-017](DEBT-017-model-architecture-cleanup.md)** | Model Architecture Cleanup (Duplicate Order Models) | P3 | Open |
| **[DEBT-015](DEBT-015-missing-api-endpoints.md)** | Missing API Endpoints (45+ endpoints) | P2-P3 | Open (Blocked by DEBT-018) |

### Recommended Order

```
DEBT-018 (Test SSOT) ← DO THIS FIRST
    ↓
DEBT-016 (CI Automation)
    ↓
DEBT-017 (Model Cleanup)
    ↓
DEBT-015 (Missing Endpoints) ← Only after foundation solid
    ↓
DEBT-014 (Friction/Design) ← Feature work
```

## Next ID Tracker

Use this ID for the next debt item:
**DEBT-019**

---

## Files

| File | Purpose |
|------|---------|
| `DEBT-018-test-ssot-stabilization.md` | **Active debt P1** - Exa fixtures, test mock drift, validation gaps |
| `DEBT-017-model-architecture-cleanup.md` | **Active debt P3** - Duplicate Order models |
| `DEBT-016-fixture-drift-ci.md` | **Active debt P2** - CI automation for fixture drift detection |
| `DEBT-015-missing-api-endpoints.md` | **Active debt P2-P3** - 45+ missing Kalshi API endpoints |
| `DEBT-014-friction-residuals.md` | **Active debt P1-P3** - friction, design decisions |
| `code-audit-checklist.md` | Periodic audit checklist / runbook (reference doc) |
| `technical-debt.md` | Living register with historical context |
| `security-audit.md` | Deep security audit findings (Agent Safety, Injection Risks) |

## Archived Source Documents (2026-01-11)

The following documents were consolidated into DEBT-014 and archived:

| Document | Archive Location | Notes |
|----------|------------------|-------|
| `friction.md` | `_archive/debt/friction.md` | User friction log - all items captured in DEBT-014 |
| `hacks.md` | `_archive/debt/hacks.md` | Hacky implementations - all P1/P2 items in DEBT-014 |
| `backwards-compatibility.md` | `_archive/debt/backwards-compatibility.md` | Compat code inventory - all items in DEBT-014 |
| `bloat.md` | `_archive/debt/bloat.md` | Bloat analysis - fully resolved (DEBT-008/009/010) |

## Workflow

- Add new debt as a short, actionable entry (priority + impact + fix path).
- Link to the relevant bug (`docs/_bugs/`) or task (`docs/_todo/`) when applicable.
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

### Recently Resolved (2026-01-11)

| ID | Title | Status |
|---|---|---|
| **[DEBT-013](../_archive/debt/DEBT-013-category-filtering-events-ssot.md)** | Category filtering SSOT: use `/events` (avoid `/markets` pagination traps) | ✅ Complete |

---

## Debt Transitions (Historical)

None. All debt items resolved or elevated to specs.

| Item | Resolution | Date |
|------|------------|------|
| DEBT-004 | Implemented via [SPEC-027](../_archive/specs/SPEC-027-settlement-timestamp.md) | 2026-01-09 |
| DEBT-002 Phase 2-3 | Closed as "Won't Fix" (see `technical-debt.md`) | 2026-01-09 |
