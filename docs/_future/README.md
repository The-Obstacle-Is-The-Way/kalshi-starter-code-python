# Future Work (Backlog)

This directory contains **future work** - items that are blocked, deferred, or planned for later.

## Distinction from `_specs/`

| Directory | Purpose | When to Use |
|-----------|---------|-------------|
| `_specs/` | **Active implementation** | Work happening NOW |
| `_future/` | **Backlog** | Blocked, deferred, or planned later |

---

## Current Backlog

### Blocked (External Dependency)

| ID | Title | Why Blocked |
|----|-------|-------------|
| **FUTURE-002** | [Kalshi Blocked Endpoints](FUTURE-002-kalshi-blocked-endpoints.md) | Subaccounts (new feature), Forecast history (no data), Institutional endpoints |

---

## Workflow

1. **New future work**: Create `FUTURE-XXX-description.md`
2. **Ready to implement**: Move to `_specs/` as `SPEC-XXX`
3. **Implemented**: Move to `_archive/`

## ID Convention

- **FUTURE-XXX** (001+): Substantial future features with full spec
- **FUTURE-00X** (00A-00Z): Small blocked/deferred items

---

## Archive (Completed)

Completed backlog items are stored under `docs/_archive/future/` (excluded from the MkDocs site
build). See [`docs/_archive/README.md`](../_archive/README.md) for the archive structure.

### Recently Promoted to Specs (2026-01-18)

| ID | Title | Status |
|---|---|---|
| [FUTURE-001](../_archive/future/FUTURE-001-exa-research-agent.md) | Exa Research Agent | ✅ Promoted → SPEC-033 |
| [TODO-00B](../_archive/future/TODO-00B-trade-executor-phase2.md) | TradeExecutor Phase 2 | ✅ Promoted → SPEC-034 |

### Recently Completed (2026-01-15)

| ID | Title | Status |
|---|---|---|
| [TODO-00A](../_archive/future/TODO-00A-api-verification-post-deadline.md) | API Verification Post-Deadline (Jan 15 cent removal) | ✅ Complete |

### Recently Completed (Ralph Wiggum Cleanup - 2026-01-09)

| ID | Title | Status |
|---|---|---|
| [TODO-009](../_archive/future/TODO-009-cent-field-deprecation-migration.md) | Cent-to-Dollar Field Migration | ✅ Complete |
| [TODO-008](../_archive/future/TODO-008-agent-safety-rails.md) | Agent Safety Rails (dry_run) | ✅ Complete |
| [TODO-007](../_archive/future/TODO-007-market-timing-safety.md) | Market Timing Safety | ✅ Complete |
| [TODO-006](../_archive/future/TODO-006-session-friction-audit.md) | Session Friction Audit | ✅ Complete |
| [TODO-005](../_archive/future/TODO-005-market-open-date-validation.md) | Market Open Date Validation | ✅ Complete |
