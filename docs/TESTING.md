# Testing (How-to)

## Install dependencies

```bash
uv sync --all-extras
```

## Quality gates (CI-like)

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/ --strict
uv run pytest -m "not integration and not slow"
```

Notes:
- `tests/e2e/` uses mocked HTTP (respx) and runs in the fast suite.
- `tests/integration/` may hit live endpoints depending on env.

## Live API integration tests

These tests require:
- `.env` (or exported env vars) with `KALSHI_KEY_ID` and key material
- `KALSHI_RUN_LIVE_API=1`

Run:

```bash
KALSHI_RUN_LIVE_API=1 uv run pytest tests/integration -m integration --timeout=60
```

