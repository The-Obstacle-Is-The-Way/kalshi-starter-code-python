# Technical Debt

This directory tracks **known debt** and **audit checklists** for the repository.

## Current Status

**6 active debt items.**

| ID | Title | Priority | Status |
|----|-------|----------|--------|
| **[DEBT-039](DEBT-039-broad-exception-catches.md)** | Broad Exception Catches Throughout Codebase | P3 | Active |
| **[DEBT-043](DEBT-043-srp-god-files.md)** | SRP — Reduce "God Files" (≤400 LoC ceiling) | P1 | Active |
| **[DEBT-044](DEBT-044-dry-cli-boilerplate.md)** | DRY — Remove Duplicated CLI Boilerplate | P1 | Active |
| **[DEBT-045](DEBT-045-complexity-noqa-methods.md)** | Complexity — Remove `# noqa: PLR0912/PLR0915` Methods | P2 | Active |
| **[DEBT-046](DEBT-046-dependency-inversion-client-factory.md)** | Dependency Inversion — Introduce a Kalshi Client Factory | P3 | Active |
| **[DEBT-047](DEBT-047-magic-numbers-policy-constants.md)** | Magic Numbers — Extract Policy-Encoding Literals to Constants | P3 | Active |

---

All resolved debt items live in `docs/_archive/debt/`.

### Recently Archived (2026-01-19)

| ID | Title | Status |
|---|---|---|
| **[DEBT-041](../_archive/debt/DEBT-041-spec-030-incomplete.md)** | SPEC-030 Has Unchecked Acceptance Criteria | ✅ Resolved |
| **[DEBT-038](../_archive/debt/DEBT-038-orchestrator-escalation-not-implemented.md)** | Orchestrator Escalation Logic Not Implemented | ✅ Resolved |
| **[DEBT-042](../_archive/debt/DEBT-042-unused-api-client-methods.md)** | Unused API Client Methods | ✅ Resolved (SPEC-043) |
| **[DEBT-040](../_archive/debt/DEBT-040-unused-synthesizer-methods.md)** | Unused Synthesizer Cost/Token Tracking Methods | ✅ Resolved |
| **[DEBT-034](../_archive/debt/DEBT-034-broad-exception-catches.md)** | Broad Exception Catches in Agent/Execution Code | ✅ Resolved |
| **[DEBT-037](../_archive/debt/DEBT-037-mock-synthesizer-production-gap.md)** | MockSynthesizer in Production Path | ✅ Resolved (SPEC-042) |
| **[DEBT-033](../_archive/debt/DEBT-033-frozen-model-setattr-hack.md)** | Frozen Pydantic Model `object.__setattr__` Hack | ✅ Closed (False Positive) |
| **[DEBT-035](../_archive/debt/DEBT-035-missing-agent-integration-tests.md)** | Missing Agent Integration Tests | ✅ Resolved |
| **[DEBT-036](../_archive/debt/DEBT-036-deep-research-timeout-hardcoded.md)** | Deep Research Timeout Hardcoded | ✅ Resolved |

### Recently Archived (2026-01-18)

| ID | Title | Status |
|---|---|---|
| **[DEBT-031](../_archive/debt/DEBT-031-floor-division-statistics.md)** | Floor Division in P&L Statistics | ✅ Archived |
| **[DEBT-032](../_archive/debt/DEBT-032-midpoint-rounding-inconsistency.md)** | Midpoint Rounding Inconsistency | ✅ Archived |

### Recently Archived (2026-01-17)

| ID | Title | Status |
|---|---|---|
| **[DEBT-014](../_archive/debt/DEBT-014-friction-residuals.md)** | Friction Residuals - Research Pipeline & Agent Design | ✅ Archived |
| **[DEBT-025](../_archive/debt/DEBT-025-subpenny-pricing-strategy.md)** | Subpenny Pricing Strategy (FixedPointDollars → rounding policy) | ✅ Archived |

### Recently Archived (2026-01-16)

| ID | Title | Status |
|---|---|---|
| **[DEBT-030](../_archive/debt/DEBT-030-trading-fees-from-settlements.md)** | Trading Fees Missing from P&L (Must Use Settlement Records) | ✅ Resolved |
| **[DEBT-029](../_archive/debt/DEBT-029-settlement-synthetic-fill-reconciliation.md)** | Settlement-as-Synthetic-Fill Reconciliation (Professional P&L) | ✅ Implemented |

### Previously Resolved (2026-01-16)

| ID | Title | Status |
|---|---|---|
| **[DEBT-018](../_archive/debt/DEBT-018-test-ssot-stabilization.md)** | Test SSOT Stabilization (Fixtures, Mocks, Exa Coverage) | ✅ Resolved |
| **[DEBT-016](../_archive/debt/DEBT-016-fixture-drift-ci.md)** | Automate Fixture Drift Detection + Weekly Re-Recording | ✅ Resolved |
| **[DEBT-015](../_archive/debt/DEBT-015-missing-api-endpoints.md)** | Missing API Endpoints - 50/74 (68%) | ✅ Complete (remaining blocked/institutional) |
| **[DEBT-028](../_archive/debt/DEBT-028-api-schema-drift-jan-2026.md)** | API Schema Drift - January 2026 Migration | ✅ Verified Working |

## Next ID Tracker

Use this ID for the next debt item:
**DEBT-048**

---

## Files

| File | Purpose |
|------|---------|
| `code-audit-checklist.md` | Periodic audit checklist / runbook (reference doc) |

## Archived Reference Docs

These are still useful references, but were moved under the archive during consolidation:

- `docs/_archive/debt/technical-debt.md` - Living register with historical context
- `docs/_archive/debt/security-audit.md` - Security findings (agent safety, injection risks)

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
- Link to the relevant bug (`docs/_bugs/`) or spec/future item (`docs/_specs/`, `docs/_future/`) when applicable.
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

### Recently Resolved (2026-01-13)

| ID | Title | Status |
|---|---|---|
| **[DEBT-017](../_archive/debt/DEBT-017-model-architecture-cleanup.md)** | Model Architecture Cleanup (Duplicate Order Models + Validation Gaps) | ✅ Complete |
| **[DEBT-019](../_archive/debt/DEBT-019-exa-empty-publisheddate-validation.md)** | Exa Empty `publishedDate` Validation Bug | ✅ Complete |
| **[DEBT-020](../_archive/debt/DEBT-020-kalshi-market-discovery-gaps.md)** | Kalshi Market Discovery Gaps (false positive / user error) | ✅ Closed |
| **[DEBT-022](../_archive/debt/DEBT-022-exa-research-task-recovery.md)** | Exa Research Task Recovery (`list_research_tasks()` crash recovery) | ✅ Complete |
| **[DEBT-023](../_archive/debt/DEBT-023-production-maturity-gaps.md)** | Production Maturity Gaps (Senior Engineer Audit) | ✅ Complete (Reference Doc) |
| **[DEBT-024](../_archive/debt/DEBT-024-cli-exit-code-policy.md)** | CLI exit code policy (not found vs empty results) | ✅ Complete |

### Recently Resolved (2026-01-14)

| ID | Title | Status |
|---|---|---|
| **[DEBT-026](../_archive/debt/DEBT-026-missing-function-docstrings.md)** | Missing Function Docstrings | ✅ Complete |
| **[DEBT-027](../_archive/debt/DEBT-027-private-function-docstrings.md)** | Private Function Docstrings | ✅ Complete |

---

## Debt Transitions (Historical)

None. All debt items resolved or elevated to specs.

| Item | Resolution | Date |
|------|------------|------|
| DEBT-004 | Implemented via [SPEC-027](../_archive/specs/SPEC-027-settlement-timestamp.md) | 2026-01-09 |
| DEBT-002 Phase 2-3 | Closed as "Won't Fix" (see `docs/_archive/debt/technical-debt.md`) | 2026-01-09 |
