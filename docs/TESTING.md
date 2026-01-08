# Testing Guide

This project follows a strict **Test-Driven Development (TDD)** workflow.
Tests are categorized into **Unit**, **Integration**, and **End-to-End (E2E)**.

## 1. Unit Tests (Fast, No IO)
Run these frequently during development. They use mocks for all external dependencies.

```bash
uv run pytest tests/unit
```

## 2. Integration Tests (Network/DB Logic)
Tests database interactions (via in-memory SQLite) and API client logic (via `respx` mocking).
These verify that requests are constructed correctly (auth headers, payloads) without hitting the real API.

```bash
uv run pytest tests/integration
```

## 3. Live API Tests (Real Network Calls)
These tests hit the **LIVE** Kalshi API. They are skipped by default for safety.

### 3.1 Public API (Safe, Read-Only)
Tests connection to public endpoints (`/markets`, `/exchange/status`). No credentials needed.

```bash
KALSHI_RUN_LIVE_API=1 uv run pytest tests/integration/api/test_public_api_live.py
```

### 3.2 Authenticated API (Requires Credentials)
Tests authenticated endpoints (`/portfolio/balance`, `/portfolio/orders`).
**WARNING:** This requires a valid API key and private key. Use the **DEMO** environment if possible.

**Prerequisites:**
Set the following environment variables (or put them in `.env`):
```bash
export KALSHI_KEY_ID="your-uuid-key-id"
export KALSHI_ENVIRONMENT="demo"  # or "prod"

# Private key: provide ONE of the following:
export KALSHI_PRIVATE_KEY_PATH="/path/to/your/private_key.pem"
# OR (for environments without filesystem access):
export KALSHI_PRIVATE_KEY_B64="<base64-encoded-private-key>"
```

**Run Command:**
```bash
uv run pytest tests/e2e/test_live_demo.py
```

## 4. Coverage Report
Check strict coverage requirements (aiming for 100% on critical modules).

```bash
uv run pytest --cov=kalshi_research --cov-report=term-missing
```
