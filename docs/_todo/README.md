# Todo Items Index

This directory contains todo/task tracking files for ongoing work.

## Current Status

**1 active item, 3 deferred/blocked items.**

## Next ID Tracker

Use this ID for the next todo you create:
**TODO-011**

---

## Active Items

| ID | Title | Priority | Status |
|----|-------|----------|--------|
| **TODO-010** | [Liquidity Analysis](TODO-010-liquidity-analysis.md) | High | Active |

---

## Deferred / Blocked Items (00X Series)

These items are either blocked by external factors or explicitly deferred for the future.

| ID | Title | Status | Blocking Condition |
|----|-------|--------|-------------------|
| **TODO-00A** | [API Verification Post-Deadline](TODO-00A-api-verification-post-deadline.md) | BLOCKED | Until Jan 15, 2026 |
| **TODO-00B** | [TradeExecutor Phase 2](TODO-00B-trade-executor-phase2.md) | DEFERRED | Until agent trading needed |
| **TODO-00C** | [Exa Research Agent](TODO-00C-exa-research-agent.md) | DEFERRED | Complex, MCP alternative exists |

---

## Archive (Completed)

Completed todo items are stored in
[`docs/_archive/todo/`](https://github.com/The-Obstacle-Is-The-Way/kalshi-starter-code-python/tree/main/docs/_archive/todo/).

Note: `docs/_archive/**` is intentionally excluded from the MkDocs site build (historical provenance only).

### Recently Completed (Ralph Wiggum Cleanup - 2026-01-09)

| ID | Title | Status |
|---|---|---|
| **TODO-009** | Cent-to-Dollar Field Migration (API Deprecation) | ✅ Complete |
| **TODO-008** | Agent Safety Rails (dry_run parameter) | ✅ Complete |
| **TODO-007** | Market Timing Safety (MarketStatusVerifier) | ✅ Complete |
| **TODO-006** | Session Friction Audit | ✅ Complete |
| **TODO-005** | Market Open Date Validation (TemporalValidator) | ✅ Complete |
| **DOCS-001** | Sync Acceptance Criteria | ✅ Complete |

### Previously Completed

| ID | Title | Status |
|---|---|---|
| **TODO-002** | Remaining Work Audit | ✅ Resolved (archived) |
| **TODO-001** | Missing Features | ✅ All Implemented |

---

## ID Naming Convention

- **TODO-XXX** (001-999): Regular actionable items
- **TODO-00X** (00A-00Z): Blocked or deferred items (placeholders)
  - When unblocked, create a proper TODO-XXX and archive the placeholder
