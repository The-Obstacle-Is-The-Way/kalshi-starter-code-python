# Archive (Historical)

This directory contains **archived** (completed/resolved) documentation.

## Structure

```text
_archive/
├── bugs/      # Resolved bug reports
├── debt/      # Resolved technical debt items
├── specs/     # Implemented specifications
└── future/    # Completed future work items
```

**Mirrors active directories:**

| Active | Archive | Contains |
|--------|---------|----------|
| `_bugs/` | `_archive/bugs/` | Resolved bugs |
| `_debt/` | `_archive/debt/` | Resolved debt |
| `_specs/` | `_archive/specs/` | Implemented specs |
| `_future/` | `_archive/future/` | Completed backlog items |

---

## Notes

- Archived docs may reference **historical file paths** that have since changed.
- For current documentation, start at `docs/index.md`.

---

## Recent Archives (Ralph Wiggum Cleanup - 2026-01-09)

### Bugs Archived

- BUG-047: Portfolio sync discrepancy
- BUG-048: Negative liquidity validation
- BUG-049: Rate limiter asymmetry
- BUG-050: Silent exception in alerts

### Debt Archived

- DEBT-001: API client typing (Pydantic models)
- DEBT-002: Magic numbers analysis (Phase 1)
- DEBT-003: Loose DB transactions

### Future Work Archived

- TODO-005: Market open date validation
- TODO-006: Session friction audit
- TODO-007: Market timing safety
- TODO-008: Agent safety rails
- TODO-009: Cent-to-dollar migration
- DOCS-001: Sync acceptance criteria
