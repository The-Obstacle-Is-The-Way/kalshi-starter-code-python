# Technical Debt

This directory tracks **known debt** and **audit checklists** for the repository.

## Files

- `docs/_debt/code-audit-checklist.md`: Periodic audit checklist / runbook.
- `docs/_debt/technical-debt.md`: Living register of known debt (add new items here).
- `docs/_debt/security-audit.md`: Deep security audit findings (Agent Safety, Injection Risks).

## Workflow

- Add new debt as a short, actionable entry (priority + impact + fix path).
- Link to the relevant bug (`docs/_bugs/`) or task (`docs/_todo/`) when applicable.
- When resolved, move the entry to the **Resolved** section (don’t delete history).
