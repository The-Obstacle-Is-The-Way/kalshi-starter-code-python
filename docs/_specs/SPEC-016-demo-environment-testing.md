# SPEC-016: Demo Environment Testing Support

**Status:** Proposed
**Priority:** P2 (Developer Experience)
**Estimated Complexity:** Low
**Dependencies:** SPEC-002 (API Client)
**Official Docs:** [docs.kalshi.com](https://docs.kalshi.com/welcome)

---

## 1. Problem Statement

### Current Issue
- All testing happens against **production API**
- No way to test order placement without real money
- Integration tests risk hitting production rate limits
- No sandbox for new developers to experiment safely

### Official Demo Environment
Kalshi provides a **demo/sandbox environment** for testing:
- Base URL: `https://demo-api.kalshi.co`
- WebSocket: `wss://demo-api.kalshi.co/trade-api/ws/v2`
- Separate credentials from production
- Safe for testing order execution

---

## 2. Solution: Environment Switching

### 2.1 Environment Configuration

```python
# src/kalshi_research/api/config.py
from enum import Enum
from pydantic import BaseModel


class Environment(str, Enum):
    """Kalshi API environments."""
    PRODUCTION = "prod"
    DEMO = "demo"


class APIConfig(BaseModel):
    """Configuration for Kalshi API client."""

    environment: Environment = Environment.PRODUCTION

    @property
    def base_url(self) -> str:
        """REST API base URL."""
        if self.environment == Environment.DEMO:
            return "https://demo-api.kalshi.co/trade-api/v2"
        return "https://api.elections.kalshi.com/trade-api/v2"

    @property
    def websocket_url(self) -> str:
        """WebSocket URL."""
        if self.environment == Environment.DEMO:
            return "wss://demo-api.kalshi.co/trade-api/ws/v2"
        return "wss://api.elections.kalshi.com/trade-api/ws/v2"


# Singleton for global access
_config = APIConfig()


def get_config() -> APIConfig:
    return _config


def set_environment(env: Environment) -> None:
    global _config
    _config = APIConfig(environment=env)
```

### 2.2 Client Updates

```python
# src/kalshi_research/api/client.py (modified)
from .config import get_config


class KalshiPublicClient:
    """Public API client with environment support."""

    def __init__(
        self,
        environment: str | None = None,  # "prod" or "demo"
        timeout: float = 30.0,
    ) -> None:
        config = get_config()
        if environment:
            from .config import Environment
            config = APIConfig(environment=Environment(environment))

        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
```

### 2.3 CLI Support

```bash
# Use demo environment
kalshi --env demo data sync-markets

# Default is production
kalshi scan movers --top 10

# Environment variable
export KALSHI_ENVIRONMENT=demo
kalshi portfolio balance
```

---

## 3. Implementation

### 3.1 Environment Variable

```bash
# .env
KALSHI_ENVIRONMENT=demo  # or "prod"
KALSHI_DEMO_API_KEY=your-demo-key
KALSHI_DEMO_PRIVATE_KEY_PATH=./keys/demo_private_key.pem
```

### 3.2 CLI Flag

```python
# src/kalshi_research/cli.py
import typer

app = typer.Typer()


@app.callback()
def main(
    env: str = typer.Option(
        "prod",
        "--env",
        "-e",
        help="API environment: prod or demo",
    ),
) -> None:
    """Kalshi Research CLI."""
    from kalshi_research.api.config import set_environment, Environment
    set_environment(Environment(env))
```

### 3.3 Test Fixtures

```python
# tests/conftest.py
import pytest
from kalshi_research.api.config import set_environment, Environment


@pytest.fixture
def demo_environment():
    """Use demo environment for tests."""
    original = get_config().environment
    set_environment(Environment.DEMO)
    yield
    set_environment(original)


@pytest.fixture
async def demo_client(demo_environment):
    """Provide demo environment client."""
    async with KalshiPublicClient(environment="demo") as client:
        yield client
```

---

## 4. Implementation Tasks

### 4.1 Phase 1: Configuration
- [ ] Create `Environment` enum
- [ ] Create `APIConfig` class with URL properties
- [ ] Add environment-specific URL resolution

### 4.2 Phase 2: Client Updates
- [ ] Update `KalshiPublicClient` to accept environment
- [ ] Update `KalshiClient` to accept environment
- [ ] Update `KalshiWebSocket` to accept environment

### 4.3 Phase 3: CLI Integration
- [ ] Add `--env` global option
- [ ] Add `KALSHI_ENVIRONMENT` env var support
- [ ] Document demo setup in README

---

## 5. Acceptance Criteria

1. **Switchable**: Can switch between prod/demo via flag or env var
2. **Isolated**: Demo credentials separate from production
3. **Safe**: Integration tests default to demo environment
4. **Documented**: Clear setup instructions for demo account

---

## 6. Demo Account Setup

### 6.1 Create Demo Account
1. Visit https://demo.kalshi.com
2. Create account with test credentials
3. Generate API keys in demo portal

### 6.2 Configure Local Environment
```bash
# Create demo key file
echo "$DEMO_PRIVATE_KEY" > keys/demo_private_key.pem
chmod 600 keys/demo_private_key.pem

# Set environment variables
export KALSHI_ENVIRONMENT=demo
export KALSHI_API_KEY=your-demo-key-id
export KALSHI_PRIVATE_KEY_PATH=./keys/demo_private_key.pem
```

### 6.3 Verify Setup
```bash
# Should connect to demo API
kalshi --env demo portfolio balance
```

---

## 7. Testing in CI

```yaml
# .github/workflows/test.yml
jobs:
  integration:
    runs-on: ubuntu-latest
    env:
      KALSHI_ENVIRONMENT: demo
      KALSHI_API_KEY: ${{ secrets.DEMO_API_KEY }}
      KALSHI_PRIVATE_KEY: ${{ secrets.DEMO_PRIVATE_KEY }}
    steps:
      - uses: actions/checkout@v4
      - name: Run integration tests
        run: |
          echo "$KALSHI_PRIVATE_KEY" > /tmp/demo_key.pem
          export KALSHI_PRIVATE_KEY_PATH=/tmp/demo_key.pem
          uv run pytest tests/integration/ -v
```

---

## 8. References

- Demo environment docs: https://docs.kalshi.com/welcome
- Demo portal: https://demo.kalshi.com
