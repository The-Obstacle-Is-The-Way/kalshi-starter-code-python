---
name: kalshi-codebase
description: Repo navigation + workflows for the Kalshi Research Platform codebase (src-layout, CLI, tests). Includes SSOT discipline and how to operate the Ralph Wiggum loop (PROMPT.md/PROGRESS.md) for iterative spec/bug implementation.
---

# Kalshi Research Platform – Codebase Guide

Use this skill when you need a **repo map**, **where-to-change-what guidance**, or to operate the **Ralph Wiggum loop** in this repository.

## SSOT rules (do not violate)

1. Code behavior in `src/kalshi_research/`
2. CLI surface in `uv run kalshi --help` / `uv run kalshi <cmd> --help`
3. Vendor docs in `docs/_vendor-docs/`
4. Internal docs/specs in `docs/`, `docs/_specs/`

If docs disagree with code, fix the docs (or open a bug/spec) rather than “believing” the docs.

## Quick start (repo navigation)

```bash
uv run kalshi --help
rg -n "SomeSymbolOrCommand" src/ tests/ docs/
```

## Repository map (what lives where)

- `src/kalshi_research/api/`: Kalshi HTTP clients + Pydantic models (`api/models/`)
- `src/kalshi_research/data/`: SQLite/SQLAlchemy persistence, repositories, fetcher, exports
- `src/kalshi_research/exa/`: Exa API client + models
- `src/kalshi_research/news/`: News tracking, collection, sentiment
- `src/kalshi_research/analysis/`: Scanner, liquidity scoring, calibration, correlations
- `src/kalshi_research/research/`: Thesis workflow + Exa-powered context/topic research
- `src/kalshi_research/cli/`: Typer CLI (`uv run kalshi ...`)
- `tests/unit/`: Unit tests mirroring `src/` layout
- `docs/_bugs/`, `docs/_specs/`, `docs/_debt/`: Trackers + implementation specs
- `docs/_ralph-wiggum/protocol.md`: Ralph Wiggum reference protocol

## Quality gates (run before any commit)

```bash
uv run pre-commit run --all-files
uv run mkdocs build --strict
uv run pytest -m "not integration and not slow"
```

## Ralph Wiggum loop (operator contract)

Canonical files:

- `PROMPT.md`: the repeated agent prompt
- `PROGRESS.md`: state file (the “brain”)
- `docs/_ralph-wiggum/protocol.md`: reference protocol

Rules of the loop:

1. Always start by reading `PROGRESS.md`.
2. Pick the **first** unchecked item and do **one** task per iteration.
3. Implement against the task doc’s **Acceptance Criteria** checkboxes:
   - `docs/_bugs/BUG-*.md`, `docs/_debt/DEBT-*.md`, `docs/_todo/TODO-*.md`, `docs/_specs/SPEC-*.md`
4. Before marking anything complete, apply the “critical claim validation” block:

```text
Review the claim or feedback (it may be from an internal or external agent). Validate every claim from first principles. If—and only if—it’s true and helpful, update the system to align with the SSOT, implemented cleanly and completely (Rob C. Martin discipline). Find and fix all half-measures, reward hacks, and partial fixes if they exist. Be critically adversarial with good intentions for constructive criticism. Ship the exact end-to-end implementation we need.
```

5. Update `PROGRESS.md`:
   - Check off the completed item **only** when all acceptance criteria are `[x]`.
   - Append a short entry to the “Work Log” section (what changed + commands run).
6. Run quality gates and only then commit (never `--no-verify`).

## Maintenance note (skills parity)

This repository keeps `.claude/skills/`, `.codex/skills/`, and `.gemini/skills/` in sync. If you update this skill,
apply the same change to all three copies.
