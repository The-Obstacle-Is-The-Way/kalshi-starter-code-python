# BUG-071: Mocked Tests Hide API Reality - No SSOT Verification

**Priority:** P1 (Systemic risk - we don't know what's true)
**Status:** ✅ Fixed (SSOT established via raw fixtures)
**Found:** 2026-01-12
**Fixed:** 2026-01-12
**Component:** Testing infrastructure, API models

---

## Resolution (SSOT Established)

We now have a concrete SSOT for Kalshi API response shapes:

- Raw production fixtures recorded to `tests/fixtures/golden/` via `scripts/record_api_responses.py`
- Sensitive fields sanitized via `scripts/sanitize_golden_fixtures.py`
- Model-vs-fixture validation via `scripts/validate_models_against_golden.py`

See **BUG-072** for the definitive response-key findings and the exact wrapper keys.

Follow-up work (CI automation and reducing mock reliance) is tracked as technical debt (see `docs/_archive/debt/DEBT-016-fixture-drift-ci.md`).

## The Problem

**We have no way to know if our Pydantic models match reality.**

Our tests mock HTTP responses with **what we expect** the API to return, not **what it actually returns**. This creates a dangerous feedback loop:

```
Code expects X → Test mocks X → Test passes → Ship it → API returns Y → Production breaks
```

### Concrete Examples Found Today

| Model | OpenAPI Says | Our Code | Reality? |
|-------|--------------|----------|----------|
| `Fill.fill_id` | REQUIRED | `Optional` | **Unknown** |
| `Fill.order_id` | REQUIRED | `Optional` | **Unknown** |
| `Fill.side` | REQUIRED | `Optional` | **Unknown** |
| `Fill.action` | REQUIRED | `Optional` | **Unknown** |
| `Order.user_id` | REQUIRED | `Optional` | **Unknown** |
| `OrderResponse.status` | Uses `status` | Uses `order_status` | Fixed with alias, but discovered by accident |

**The OpenAPI spec claims these fields are required. Our models treat them as optional. Both can't be right. We have no empirical data to know which is true.**

---

## Why This Is P1

1. **Financial risk**: Trading responses (`create_order`, `amend_order`, `cancel_order`) could fail silently or throw after the trade is placed
2. **Silent corruption**: If API adds/removes fields, we won't know until production breaks
3. **False confidence**: 596 tests pass, but they're testing our assumptions, not reality
4. **Documentation drift**: Kalshi's OpenAPI spec may be aspirational, not actual

### The BUG-069 Near-Miss

We discovered `OrderResponse` expected `order_status` but API sends `status`. This was caught **by code review**, not by tests. The tests passed because they mocked `order_status`. If this had reached production with live trading:

1. Order placed successfully on Kalshi
2. Response parsing fails (Pydantic validation error)
3. Exception thrown AFTER money moved
4. We lose track of the order ID
5. Can't cancel/manage an order we don't know exists

---

## Root Cause Analysis

### 1. No Integration Tests Hit Real API

```bash
$ ls tests/integration/api/
test_client.py              # Uses respx mocks
test_trading_integration.py # Uses respx mocks
```

Even "integration" tests use `respx` to mock HTTP. No test ever hits `api.elections.kalshi.com` or `demo-api.kalshi.co`.

### 2. Unit Test Mocks Return Expected Values

```python
# tests/unit/api/test_trading.py:33-36
mock_client._client.post.return_value = MagicMock(
    status_code=201,
    json=lambda: {"order": {"order_id": "oid-123", "status": "resting"}},  # We made this up
)
```

This tests that our code handles `{"status": "resting"}` correctly. It does NOT test that Kalshi actually sends `{"status": "resting"}`.

### 3. OpenAPI Spec May Be Wrong

Kalshi's `https://docs.kalshi.com/openapi.yaml` says `Fill.fill_id` is REQUIRED. But our code treats it as Optional and **works in production**. Possible explanations:

- OpenAPI is wrong (documentation drift)
- API sends it but we're not using it
- Different endpoints return different shapes
- They changed it and didn't update docs

**We don't know which is true.**

---

## Finding the SSOT (Single Source of Truth)

The only SSOT is **what the API actually returns**. Not OpenAPI. Not our models. Not our tests.

### Option A: Record Real API Responses (Recommended)

Create a "golden file" test pattern:

```python
# tests/integration/api/test_real_responses.py

import json
from pathlib import Path

GOLDEN_DIR = Path("tests/fixtures/golden")

@pytest.mark.integration
@pytest.mark.real_api  # Skip in CI, run manually
async def test_record_fill_response():
    """Record actual API response for Fill endpoint."""
    async with KalshiClient(...) as client:
        fills = await client.get_fills(limit=1)

        # Save actual response
        golden_file = GOLDEN_DIR / "fill_response.json"
        golden_file.write_text(json.dumps(fills.model_dump(), indent=2))

        # Or compare against existing golden file
        if golden_file.exists():
            expected = json.loads(golden_file.read_text())
            assert fills.model_dump() == expected, "API response changed!"
```

### Option B: Response Schema Validator

Add runtime validation that logs unexpected fields:

```python
# src/kalshi_research/api/client.py

def _validate_response(data: dict, model: type[BaseModel], endpoint: str) -> None:
    """Log any fields in response that aren't in our model."""
    model_fields = set(model.model_fields.keys())
    response_fields = set(data.keys())

    unexpected = response_fields - model_fields
    if unexpected:
        logger.warning(
            "API returned unexpected fields",
            endpoint=endpoint,
            unexpected_fields=list(unexpected),
            data_sample=str(data)[:500],
        )

    missing = model_fields - response_fields
    required_missing = [f for f in missing if model.model_fields[f].is_required()]
    if required_missing:
        logger.warning(
            "API missing fields we marked required",
            endpoint=endpoint,
            missing_required=required_missing,
        )
```

### Option C: API Response Recorder Middleware

Record all API responses to a debug file during development:

```python
# Middleware that captures real responses
class ResponseRecorder:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    async def record(self, endpoint: str, response: dict):
        filename = f"{endpoint.replace('/', '_')}_{datetime.now().isoformat()}.json"
        (self.output_dir / filename).write_text(json.dumps(response, indent=2))
```

Then diff these against our Pydantic model expectations.

### Option D: Contract Testing with Pact

Use a contract testing framework to verify API compatibility:

```python
# Consumer-driven contract test
from pact import Consumer, Provider

pact = Consumer('kalshi-research').has_pact_with(Provider('kalshi-api'))

@pact.verify
def test_fill_contract():
    pact.given("fills exist").upon_receiving("a fill request").with_request(
        method="GET", path="/portfolio/fills"
    ).will_respond_with(
        status=200,
        body={
            "fills": EachLike({
                "fill_id": Like("f-123"),  # Must be present
                "trade_id": Like("t-456"),
                # ... define expected shape
            })
        }
    )
```

---

## Fix Applied (2026-01-12)

- Recorded raw production fixtures to `tests/fixtures/golden/` via `scripts/record_api_responses.py`
- Added deterministic sanitization via `scripts/sanitize_golden_fixtures.py` (IDs, money-like fields, tickers)
- Added model-vs-fixture validator `scripts/validate_models_against_golden.py`
- Updated models + vendor docs to match observed wrapper keys and payload fields

Follow-up hardening is tracked as debt:
- `docs/_archive/debt/DEBT-016-fixture-drift-ci.md` (automation)
- `docs/_archive/debt/DEBT-018-test-ssot-stabilization.md` (fixture-driven tests, Exa SSOT)

---

## Endpoints to Verify (Priority Order)

### Critical (Trading - Money at Risk)

| Endpoint | Method | Model |
|----------|--------|-------|
| `/portfolio/orders` | POST | `OrderResponse` |
| `/portfolio/orders/{id}/amend` | POST | `OrderResponse` |
| `/portfolio/orders/{id}` | DELETE | `CancelOrderResponse` |

### High (Portfolio Accuracy)

| Endpoint | Method | Model |
|----------|--------|-------|
| `/portfolio/fills` | GET | `Fill` |
| `/portfolio/orders` | GET | `Order` |
| `/portfolio/positions` | GET | `PortfolioPosition` |
| `/portfolio/balance` | GET | `PortfolioBalance` |

### Medium (Market Data)

| Endpoint | Method | Model |
|----------|--------|-------|
| `/markets` | GET | `Market` |
| `/markets/{ticker}` | GET | `Market` |
| `/markets/{ticker}/orderbook` | GET | `Orderbook` |

---

## Acceptance Criteria

- [x] Golden fixtures exist for all Critical and High priority endpoints
- [x] Pydantic models match actual API responses (not OpenAPI, not guesses)
- [ ] At least one test per endpoint uses golden fixture instead of hand-crafted mock (DEBT-018)
- [ ] Runtime validator logs unexpected fields (non-blocking) (DEBT-016)
- [x] Documentation updated with "Verified against API" dates

---

## Related

- **BUG-069**: `OrderResponse` field mismatch (discovered this pattern)
- **BUG-066**: Fill model "required" fields marked optional
- **BUG-067**: Order model "required" fields marked optional
- **DEBT-015**: Missing API endpoints (more surface area for this problem)

---

## The Uncomfortable Truth

> "All happy unit tests are alike; each broken production system is broken in its own way."

Our tests pass because we control both the question and the answer. That's not testing - that's confirmation bias with extra steps.
