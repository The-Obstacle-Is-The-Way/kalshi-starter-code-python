# Testing (How-to)

Commands and conventions for running tests locally and in CI.

## Test tiers (and what can cost money)

This repo intentionally separates tests by **confidence level** and **cost/risk profile**:

- **Unit tests** (`tests/unit/`): no network, no paid APIs, fastest feedback.
- **Integration tests** (`tests/integration/`): real components (DB/migrations/CLI) with **mocked HTTP** via
  `respx` by default.
- **E2E tests** (`tests/e2e/`): full CLI pipelines + real SQLite + mocked HTTP (still no paid APIs).
- **Live API tests** (opt-in): hit real vendor APIs (Kalshi, Exa). These can:
  - consume rate limits,
  - cost money (Exa),
  - or create operational risk if misconfigured (authenticated endpoints).

## Fast local suite (CI-like)

```bash
uv run pytest -m "not integration and not slow"
```

## Unit tests

Unit tests are under `tests/unit/` and aim to test real logic with mocking only at **system boundaries**
(HTTP, filesystem, process spawning).

```bash
uv run pytest tests/unit
```

## Integration tests

Integration tests are under `tests/integration/` and cover:

- DB migrations + repositories
- CLI smoke/integration tests
- API client behavior via `respx` mocking

```bash
uv run pytest tests/integration
```

## E2E tests

E2E tests are under `tests/e2e/` and run full pipelines with mocked HTTP + real SQLite.

```bash
uv run pytest tests/e2e
```

## CI wiring (GitHub Actions)

Current CI configuration is in `.github/workflows/ci.yml`:

- `lint` job: `ruff`, `mypy`, `mkdocs build --strict`
- `test` job: unit tests (coverage) + mocked E2E tests (runs on Python 3.11/3.12/3.13 matrix)
- `integration` job: runs `tests/integration/` **only on push to `main`**
  - Live tests are still skipped unless explicitly enabled via env vars.

**CI cost note:** GitHub Actions usage can cost money depending on repo visibility and plan (minutes ×
matrix size). The tests themselves are mostly mocked; external API costs only apply if live tests are
explicitly enabled.

## Live API tests (disabled by default)

Some integration/e2e tests can hit the live Kalshi API, but only when explicitly enabled:

```bash
KALSHI_RUN_LIVE_API=1 uv run pytest tests/integration/api/test_public_api_live.py
```

There is also an opt-in demo “smoke” E2E test:

```bash
uv run pytest tests/e2e/test_live_demo.py -q
```

It runs only when `KALSHI_KEY_ID`, `KALSHI_PRIVATE_KEY_PATH`, and `KALSHI_ENVIRONMENT=demo` are set.

Authenticated live tests additionally require credentials in your environment or `.env`:

```bash
export KALSHI_KEY_ID="your-key-id"
export KALSHI_ENVIRONMENT="demo"  # or "prod"
export KALSHI_PRIVATE_KEY_PATH="/path/to/your/private_key.pem"
# OR:
export KALSHI_PRIVATE_KEY_B64="<base64-encoded-private-key>"
```

## Exa live tests (disabled by default)

Some integration tests use the real Exa API (skipped automatically unless `EXA_API_KEY` is set):

```bash
EXA_API_KEY="your-exa-api-key" uv run pytest tests/integration/exa/test_exa_research.py -q
```

**Exa cost note:** this test will make a real Exa request and will incur API cost.

## Recommended cadence (A+ practice)

- **Every PR:** lint + unit + mocked E2E (no live network).
- **Daily or on merge to main:** mocked integration tests (DB/migrations/CLI) to catch wiring drift early.
- **Scheduled (nightly/weekly):** live API contract checks (Kalshi public/authenticated; Exa) using canary
  credentials and explicit budgets/limits.

## Coverage

```bash
uv run pytest tests/unit --cov=kalshi_research --cov-report=term-missing --cov-report=xml
```
