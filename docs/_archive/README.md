# Archive (Historical)

This directory contains **archived** internal documentation (specs, bugs, debt, and TODO audits).

## Structure

```text
_archive/
├── bugs/      # Resolved bug reports
├── debt/      # Resolved technical debt items
├── specs/     # Implemented specifications
└── todo/      # Completed TODO items
```

## Notes

- Archived docs may reference **historical file paths** and behaviors that have since changed.
- The CLI previously lived in `src/kalshi_research/cli.py` and is now a package at
  `src/kalshi_research/cli/`.
- For current documentation, start at `docs/index.md` and `docs/developer/cli-reference.md`.

---

## Recent Archives (Ralph Wiggum Cleanup - 2026-01-09)

### Bugs Archived

- BUG-047: Portfolio sync discrepancy (Kalshi API behavior)
- BUG-048: Negative liquidity validation
- BUG-049: Rate limiter asymmetry
- BUG-050: Silent exception in alerts

### Debt Archived

- DEBT-001: API client typing (Pydantic models)
- DEBT-002: Magic numbers analysis (Phase 1)
- DEBT-003: Loose DB transactions

### TODOs Archived

- TODO-005: Market open date validation
- TODO-006: Session friction audit
- TODO-007: Market timing safety
- TODO-008: Agent safety rails
- TODO-009: Cent-to-dollar migration
- DOCS-001: Sync acceptance criteria
