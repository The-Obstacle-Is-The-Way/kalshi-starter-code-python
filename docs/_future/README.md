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

| ID | Title | Blocking Condition |
|----|-------|-------------------|
| **FUTURE-00A** | [API Verification Post-Deadline](TODO-00A-api-verification-post-deadline.md) | Until Jan 15, 2026 |

### Deferred (Not Priority)

| ID | Title | Why Deferred |
|----|-------|--------------|
| **FUTURE-001** | [Exa Research Agent](FUTURE-001-exa-research-agent.md) | Complex (~20hrs), MCP alternative exists |
| **FUTURE-00B** | [TradeExecutor Phase 2](TODO-00B-trade-executor-phase2.md) | Until agent trading needed |

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

### Recently Completed (Ralph Wiggum Cleanup - 2026-01-09)

| ID | Title | Status |
|---|---|---|
| [TODO-009](../_archive/future/TODO-009-cent-field-deprecation-migration.md) | Cent-to-Dollar Field Migration | ✅ Complete |
| [TODO-008](../_archive/future/TODO-008-agent-safety-rails.md) | Agent Safety Rails (dry_run) | ✅ Complete |
| [TODO-007](../_archive/future/TODO-007-market-timing-safety.md) | Market Timing Safety | ✅ Complete |
| [TODO-006](../_archive/future/TODO-006-session-friction-audit.md) | Session Friction Audit | ✅ Complete |
| [TODO-005](../_archive/future/TODO-005-market-open-date-validation.md) | Market Open Date Validation | ✅ Complete |
