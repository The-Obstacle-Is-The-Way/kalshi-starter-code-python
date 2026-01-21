# DEBT-046: Dependency Inversion — Introduce a Kalshi Client Factory

## Status

- **Severity:** MEDIUM
- **Effort:** M (0.5–1 day)
- **Blocking:** No (but it reduces future refactor pain)
- **Target Date:** 2026-02-12
- **Status:** ✅ Resolved (2026-01-20)

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

Current counts (2026-01-20 audit, SSOT verified):

- `KalshiPublicClient(` in CLI: **0** (excluding `client_factory.py` and `TYPE_CHECKING`)
- `KalshiClient(` in CLI: **0** (excluding `client_factory.py` and `TYPE_CHECKING`)

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

- [x] `rg -n \"KalshiPublicClient\\(\" src/kalshi_research/cli` returns **0** (excluding `client_factory.py` and `TYPE_CHECKING`)
- [x] `rg -n \"KalshiClient\\(\" src/kalshi_research/cli` returns **0** (excluding `client_factory.py` and `TYPE_CHECKING`)
- [x] All tests pass: `uv run pytest`
- [x] All quality gates pass: `uv run pre-commit run --all-files`

## Acceptance Criteria

- [x] Implement `cli/client_factory.py` (single SSOT for client construction) - **DONE (salvaged from ralph-wiggum-loop)**
- [x] Migrate all CLI modules to use the factory functions (**0** direct `KalshiPublicClient()` / `KalshiClient()` instantiations remain)
- [x] Update unit tests to patch factory functions (avoid constructor patch leakage)

**Note (2026-01-20):** Some CLI tests were order-dependent after introducing `client_factory` because patching
`kalshi_research.api.KalshiPublicClient` can be captured at import-time. Tests now patch
`kalshi_research.cli.client_factory.public_client` / `authed_client` directly to avoid leakage.
