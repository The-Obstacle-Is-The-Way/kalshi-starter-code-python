# Technical Debt

This directory tracks **known debt** and **audit checklists** for the repository.

## Current Status

**0 active debt items.** All tracked debt from Ralph Wiggum cleanup resolved.

## Next ID Tracker

Use this ID for the next debt item:
**DEBT-004**

---

## Files

- `docs/_debt/code-audit-checklist.md`: Periodic audit checklist / runbook (reference doc).
- `docs/_debt/technical-debt.md`: Living register of known debt (add new items here).
- `docs/_debt/security-audit.md`: Deep security audit findings (Agent Safety, Injection Risks).

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

---

## Remaining Debt (Low Priority)

These are documented in `technical-debt.md` but not blocking:

| Category | Description | Priority |
|----------|-------------|----------|
| DEBT-002 Phase 2 | Extract strategy defaults to `AnalysisConfig` | Low |
| DEBT-002 Phase 3 | Inject config into `MarketScanner`/`EdgeDetector` | Low |
