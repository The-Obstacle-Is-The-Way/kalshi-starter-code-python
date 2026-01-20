# DEBT-046: Dependency Inversion — Introduce a Kalshi Client Factory

## Status

- **Severity:** MEDIUM
- **Effort:** M (0.5–1 day)
- **Blocking:** No (but it reduces future refactor pain)
- **Target Date:** 2026-02-12
- **Status:** Active

## Problem

CLI commands directly instantiate concrete API clients (`KalshiPublicClient()` / `KalshiClient()`).
This causes:

- repeated environment/credential resolution logic
- harder testing (must patch constructors instead of injecting a boundary)
- harder global changes (timeouts, retry policy, headers, base URL)

## Evidence

Reproduce:

```bash
rg -n \"KalshiPublicClient\\(\" src/kalshi_research/cli | wc -l
rg -n \"KalshiClient\\(\" src/kalshi_research/cli | wc -l
```

Current counts (2026-01-19 audit, SSOT verified):

- `KalshiPublicClient(` in CLI: **29** (not counting client_factory.py)
- `KalshiClient(` in CLI: **2** (not counting client_factory.py)

## Solution (Minimal, Not Framework DI)

Create a tiny factory module (suggested: `src/kalshi_research/cli/client_factory.py`):

- `def public_client(*, environment: str | None = None, timeout: float | None = None) -> KalshiPublicClient`
- `def authed_client(*, environment: str | None = None, timeout: float | None = None) -> KalshiClient`

Responsibilities:

1. Single place to resolve environment + config
2. Single place to set defaults (timeouts, retries)
3. Easy to patch in tests (patch factory functions, not client constructors)

Then update CLI modules to use:

```python
async with public_client(environment=environment) as client:
    ...
```

## Definition of Done (Objective)

- [ ] `rg -n \"KalshiPublicClient\\(\" src/kalshi_research/cli` returns **0** (excluding client_factory.py and TYPE_CHECKING)
- [ ] `rg -n \"KalshiClient\\(\" src/kalshi_research/cli` returns **0** (excluding client_factory.py)
- [x] All tests pass: `uv run pytest`
- [x] All quality gates pass: `uv run pre-commit run --all-files`

## Acceptance Criteria

- [x] Implement `cli/client_factory.py` (single SSOT for client construction) - **DONE (salvaged from ralph-wiggum-loop)**
- [ ] Migrate all CLI modules to use the factory functions (0/29 KalshiPublicClient, 0/2 KalshiClient migrated)
- [ ] Update unit tests to patch factory instead of constructors

**Note (2026-01-19):** The `client_factory.py` module and its tests were salvaged from the defunct `ralph-wiggum-loop` branch. The CLI module migration work was lost and needs to be redone.
