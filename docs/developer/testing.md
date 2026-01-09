# Testing (How-to)

Commands and conventions for running tests locally and in CI.

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

## Live API tests (disabled by default)

Some integration/e2e tests can hit the live Kalshi API, but only when explicitly enabled:

```bash
KALSHI_RUN_LIVE_API=1 uv run pytest tests/integration/api/test_public_api_live.py
```

Authenticated live tests additionally require credentials in your environment or `.env`:

```bash
export KALSHI_KEY_ID="your-key-id"
export KALSHI_ENVIRONMENT="demo"  # or "prod"
export KALSHI_PRIVATE_KEY_PATH="/path/to/your/private_key.pem"
# OR:
export KALSHI_PRIVATE_KEY_B64="<base64-encoded-private-key>"
```

## Coverage

```bash
uv run pytest tests/unit --cov=kalshi_research --cov-report=term-missing --cov-report=xml
```
