---
name: kalshi-doc-audit
description: Audit and correct Kalshi Research Platform documentation/specs against SSOT (code, CLI help, OpenAPI/vendor docs), and record any drift in docs/_bugs, docs/_todo, or docs/_debt.
---

# Documentation Audit

## SSOT hierarchy

1. Code behavior in `src/kalshi_research/`
2. CLI surface in `uv run kalshi --help` / `uv run kalshi <cmd> --help`
3. Vendor OpenAPI / official docs (`docs/_vendor-docs/`)
4. Internal docs/specs (`docs/`, `docs/_specs/`)

## Audit checklist (repeatable)

1. Validate docs build and internal links:
   - `uv run mkdocs build --strict`
2. Validate CLI docs against help output:
   - Spot-check each command group: `uv run kalshi data --help`, `... market --help`, etc.
3. Validate configuration docs against actual env var usage:
   - Search code for `os.getenv("KALSHI_")` and ensure docs match.
4. When you find drift:
   - Fix the doc/spec directly.
   - If it’s a known limitation or a deliberate compromise, record it in:
     - `docs/_bugs/` (active bug), or
     - `docs/_todo/` (planned work), or
     - `docs/_debt/` (accepted technical debt).
5. Run quality gates before committing:
   - `uv run pre-commit run --all-files`

## Key indexes

- Docs entrypoint: `docs/index.md`
- Active specs: `docs/_specs/README.md`
- Vendor references: `docs/_vendor-docs/`
