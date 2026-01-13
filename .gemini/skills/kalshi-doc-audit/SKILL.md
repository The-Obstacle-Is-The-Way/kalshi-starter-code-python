---
name: kalshi-doc-audit
description: Audits and corrects Kalshi Research Platform documentation/specs against SSOT (code, CLI help, vendor docs), and records any drift in docs/_bugs, docs/_future, or docs/_debt.
---

# Documentation Audit

## SSOT hierarchy

1. Code behavior in `src/kalshi_research/`
2. CLI surface in `uv run kalshi --help` / `uv run kalshi <cmd> --help`
3. Vendor docs (`docs/_vendor-docs/`)
4. Internal docs/specs (`docs/`, `docs/_specs/`)

## Audit checklist (repeatable)

1. Validate docs build and internal links:
   - `uv run mkdocs build --strict`
2. Validate CLI docs against help output:
   - Spot-check each command group: `uv run kalshi data --help`, `... market --help`, etc.
3. Validate configuration docs against actual env var usage:
   - Search code for `os.getenv("KALSHI_")` / `os.getenv("EXA_")` and ensure docs match.
4. When you find drift:
   - Fix the doc/spec directly.
   - If it's a known limitation or a deliberate compromise, record it in:
     - `docs/_bugs/` (active bug), or
     - `docs/_future/` (planned/deferred work), or
     - `docs/_debt/` (accepted technical debt).
   - Keep trackers consistent with their indexes:
     - `docs/_bugs/README.md`, `docs/_future/README.md`, `docs/_debt/README.md`
5. Run quality gates before committing:
   - `uv run pre-commit run --all-files`

## Key indexes

- Docs entrypoint: `docs/index.md`
- Active specs: `docs/_specs/README.md`
- Vendor references: `docs/_vendor-docs/`

## Safety notes

- Never delete `data/kalshi.db` to "fix" corruption; diagnose and recover instead.
- `data/exa_cache/` is disposable cache; keep it out of git.
