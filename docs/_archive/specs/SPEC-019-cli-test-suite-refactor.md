# SPEC-019: CLI Test Suite Refactor

## Status
- **State**: Implemented
- **Created**: 2026-01-08
- **Completed**: 2026-01-08
- **Archived**: 2026-01-08
- **Target Version**: 0.2.0

## Context
The CLI was refactored from a monolithic `cli.py` into a modular Typer package under
`src/kalshi_research/cli/`. However, the CLI unit tests remained in two monolithic files:

- `tests/unit/test_cli.py`
- `tests/unit/test_cli_extended.py`

This created a mismatch between the production structure and the test suite structure, making the
CLI tests harder to navigate, extend, and review.

## Objectives
- Mirror the CLI package structure under `tests/unit/cli/`.
- Keep each test module focused on a single CLI sub-app (market/data/alerts/etc).
- Preserve existing CLI test coverage and behavior.
- Reduce “god test file” risk (high merge conflict rate, hard-to-find tests).

## Proposed Test Structure

```text
tests/unit/cli/
├── __init__.py
├── conftest.py          # Shared CliRunner + optional global state reset
├── test_app.py          # Top-level app + global flags (e.g., --env)
├── test_market.py       # `kalshi market ...`
├── test_data.py         # `kalshi data ...`
├── test_alerts.py       # `kalshi alerts ...`
├── test_scan.py         # `kalshi scan ...`
├── test_analysis.py     # `kalshi analysis ...`
├── test_research.py     # `kalshi research ...`
└── test_portfolio.py    # `kalshi portfolio ...`
```

## Design Notes
- Mock only at system boundaries:
  - HTTP clients (`KalshiPublicClient`, `KalshiClient`)
  - DB manager/session creation (`DatabaseManager`, repositories)
  - Filesystem read/write where required (alerts/theses JSON)
- Prefer `runner.isolated_filesystem()` for tests that write local JSON, `.env`, or DB stubs.
- Keep assertions resilient to Rich table formatting (assert on key substrings, not exact tables).

## Implementation Checklist
- [x] Create `tests/unit/cli/` and split tests by CLI module responsibility.
- [x] Remove the old monolithic CLI test files to avoid duplication.
- [x] Ensure `pytest` collection remains stable and unit tests pass.
- [x] Ensure `ruff`, `mypy`, and pre-commit quality gates pass.
