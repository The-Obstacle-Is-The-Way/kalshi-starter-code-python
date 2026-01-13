# DEBT-018: Test SSOT Stabilization (Fixtures, Mocks, Exa Coverage)

**Priority:** P1 (Foundation stability before new features)
**Status:** 🟡 In Progress
**Created:** 2026-01-12
**Related:** DEBT-016, DEBT-017, BUG-071

---

## Summary

Deep analysis revealed that while Kalshi API golden fixtures exist, the test suite has significant gaps:

1. **Tests use inline mocks that drift from golden fixtures** - 70%+ field coverage gap
2. **Some tests still mock at the wrong layer** (entire clients / MagicMock models) - real parsing errors can slip

**Status update (2026-01-12):**
- ✅ Exa SSOT baseline added (golden fixtures + model validation + unit tests)
- ✅ Kalshi public SSOT gaps closed (trades + candlesticks fixtures + unit tests)
- 🔴 Remaining: CLI test architecture cleanup (Phase 4) + optional “inline mock drift” guard (Phase 2 optional)

**Status update (2026-01-13):**
- ✅ Phase 4 completed for core CLI entrypoints (`market`, `portfolio balance`, `scan`):
  - CLI tests now mock at the HTTP boundary (`respx`) and exercise real Pydantic parsing.
  - Added a smoke test proving malformed API payloads fail the CLI cleanly.
- 🔴 Remaining: Phase 2 optional drift guard (and lower-priority CLI test modules still using patch-based clients).

This debt must be paid before adding new features to ensure a stable foundation.

---

## Problem 1 (Resolved): Exa SSOT Validation

### Current State

| Component | Files | Golden Fixtures | Risk |
|-----------|-------|-----------------|------|
| Exa client | 12 source files | **7** | Low |
| Exa tests | 5 test modules (+2 `__init__.py`), ~16 `respx` route mocks | Golden + inline | Medium |

### Impact

- If Exa changes their API response structure, tests pass but production breaks
- No way to detect drift without manually comparing to real API
- Fast-moving AI APIs change frequently (high likelihood)

### Files Involved

**Source:**
- `src/kalshi_research/exa/client.py` - Main client
- `src/kalshi_research/exa/models/*.py` - 6 model files (search, answer, contents, etc.)

**Tests (all use inline mocks):**
- `tests/unit/exa/test_client.py` - 250+ lines, `@respx.mock` for API routes
- `tests/unit/exa/test_config.py`
- `tests/unit/exa/test_models.py`
- `tests/unit/exa/test_cache.py`
- `tests/integration/exa/test_exa_research.py`

### Recommended Fix

1. Create `tests/fixtures/golden/exa/` directory
2. Record real Exa API responses (requires EXA_API_KEY):
   - `search_response.json`
   - `search_and_contents_response.json`
   - `find_similar_response.json`
   - `answer_response.json`
   - `get_contents_response.json`
   - `research_task_create_response.json` (create response)
   - `research_task_response.json` (terminal response)
3. Add to `scripts/record_api_responses.py` or create `scripts/record_exa_responses.py`
4. Validate Exa models against golden fixtures

**Effort:** Medium (script + fixture recording + validation)

### Completed (2026-01-12)

- `scripts/record_exa_responses.py` records `/search`, `/contents`, `/findSimilar`, `/answer` fixtures.
- `scripts/record_exa_responses.py --only-research` records `/research/v1` fixtures without re-recording core endpoints.
- `scripts/validate_models_against_golden.py` validates Exa models against those fixtures.
- Unit tests validate the recorded fixtures against Exa response models.

---

## Problem 2: Test Mocks Drift from Golden Fixtures

### Current State

Tests create inline mock responses instead of loading golden fixtures. This creates drift risk.

### Drift Analysis

| Component | Inline Mock Fields | Golden Fixture Fields | Gap |
|-----------|-------------------|----------------------|-----|
| Market | 20 fields (`tests/conftest.py:make_market`) | 51 fields (`market_single_response.json`) | **31 fields missing** |
| Order | 2–3 fields (common mocks) | 27 fields (`portfolio_orders_response.json`) | **24–25 fields missing** |
| Position | 2 fields | 12 fields | **10 fields missing** |
| Orderbook | 2 fields (legacy only) | 4 fields (incl. dollar) | dollar fields |
| Create Order Response | 2 fields (common mocks) | 26 fields (`create_order_response.json`) | **24 fields missing** |

### Example: Order Mock Drift

**Test mock** (`tests/unit/api/test_trading.py`):
```python
json={"order": {"order_id": "oid-123", "status": "resting"}}
```

**Golden fixture payload** (`tests/fixtures/golden/create_order_response.json` → `response.order`):
```json
{
  "order_id": "...",
  "status": "resting",
  "action": "buy",
  "client_order_id": "...",
  "created_time": "...",
  "fill_count": 0,
  "initial_count": 10,
  "maker_fees": 0,
  "taker_fees": 0,
  "taker_fill_cost": 0,
  "taker_fill_cost_dollars": "0.0000"
  // ... +16 more fields in production
}
```

### Files with Drift Risk

| File | Issue |
|------|-------|
| `tests/conftest.py` | `make_market()`, `make_orderbook()` factories simplified |
| `tests/unit/api/test_client.py` | `mock_market_response` inline fixture |
| `tests/unit/api/test_trading.py` | Order responses oversimplified |
| `tests/unit/api/test_client_extended.py` | Position/order mocks minimal |
| `tests/e2e/test_data_pipeline.py` | `_event_dict()`, `_market_dict()` inline |

### Recommended Fix

**Option A (Preferred): Load Golden Fixtures in Tests**
```python
# Instead of inline dict
@pytest.fixture
def mock_market_response():
    with open("tests/fixtures/golden/market_single_response.json") as f:
        return json.load(f)["response"]
```

**Option B: Validate Inline Mocks Against Golden**
- Add CI step that compares inline mock keys vs golden fixture keys
- Fail if inline mock is missing required fields

**Effort:** Medium (refactor ~10 test files)

---

## Problem 3 (Resolved): Missing Kalshi Fixture Validation

### Endpoints Without Golden Fixture Validation

| Endpoint | Golden Fixture | Unit Test | Model Validated |
|----------|----------------|-----------|-----------------|
| `get_trades()` | ✅ `trades_list_response.json` | ✅ Yes | ✅ Yes |
| `get_candlesticks()` | ✅ `candlesticks_batch_response.json` | ✅ Yes | ✅ Yes |
| `get_series_candlesticks()` | ✅ `series_candlesticks_response.json` | ✅ Yes | ✅ Yes |
| `get_event()` | ✅ `event_single_response.json` | ✅ Yes | ✅ Yes |

### Impact

- These endpoints are now validated against recorded SSOT fixtures.

### Recommended Fix

1. **Record trades fixture:**
   ```bash
   # Add a new public recording step in scripts/record_api_responses.py.
   # IMPORTANT: record the RAW response payload (not parsed Trade models).
   #
   # Example:
   # await _record_public_get(
   #     client,
   #     label="trades",
   #     path="/markets/trades",
   #     params={"ticker": "<LIVE_TICKER>", "limit": 5},
   #     save_as="trades_list",
   #     results=results,
   # )
   ```

2. **Add series candlesticks test + fixture:**
   - Record from real API
   - Add test in `test_client.py`

3. **Add get_event test:**
   - Fixture already exists (`event_single_response.json`)
   - Just need test method

**Effort:** Completed

---

## Problem 4: CLI Tests Mock at Wrong Layer

### Current Pattern (Wrong)

```python
# tests/unit/cli/test_market.py (CURRENT - WRONG)
@patch("kalshi_research.api.KalshiPublicClient")
def test_market_get(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client_cls.return_value = mock_client

    mock_market = MagicMock()
    mock_market.ticker = "TEST-MARKET"
    mock_market.status.value = "active"  # MagicMock, not real enum
    mock_market.yes_bid_cents = 50       # Property doesn't exist on MagicMock
    mock_client.get_market.return_value = mock_market  # Returns MagicMock, not Market
```

### Correct Pattern (from `tests/unit/api/test_client.py`)

```python
# tests/unit/api/test_client.py (CORRECT - HTTP boundary mock)
@pytest.mark.asyncio
@respx.mock
async def test_get_market_success(self, mock_market_response: dict[str, Any]) -> None:
    ticker = "KXBTC-25JAN-T100000"
    respx.get(f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}").mock(
        return_value=Response(200, json=mock_market_response)
    )

    async with KalshiPublicClient() as client:
        market = await client.get_market(ticker)  # Returns REAL Market model

    assert market.ticker == ticker
    assert market.status == MarketStatus.ACTIVE  # Real enum, not MagicMock
```

### Why Current Pattern is Dangerous

| Issue | Impact |
|-------|--------|
| `MagicMock` returns `MagicMock` for any attribute | Tests pass even if CLI accesses non-existent fields |
| No Pydantic validation | API response structure changes won't be caught |
| `mock_market.status.value = "active"` | Real `MarketStatus` enum doesn't work like this |
| `mock_market.yes_bid_cents` | Property computed from `yes_bid`, but MagicMock doesn't compute |

### Files Requiring Refactor

| File | Tests | Mocking Pattern | Priority |
|------|-------|-----------------|----------|
| `tests/unit/cli/test_market.py` | 20 tests | `@patch("...KalshiPublicClient")` | P3-High |
| `tests/unit/cli/test_portfolio.py` | 16 tests | `@patch("...KalshiClient")` + `@patch("...DatabaseManager")` | P3-Medium |
| `tests/unit/cli/test_scan.py` | ~5 tests | `@patch("...KalshiPublicClient")` | P3-Medium |
| `tests/unit/cli/test_data.py` | ~8 tests | Mixed | P3-Low |
| `tests/unit/cli/test_research.py` | ~10 tests | `@patch` Exa client | P3-Low |

### Explicit Implementation Plan

#### Step 1: Create CLI test fixtures module

```python
# tests/unit/cli/fixtures.py (NEW)
"""Golden fixture loaders for CLI tests."""
from tests.golden_fixtures import load_golden_response

def load_market_fixture() -> dict[str, Any]:
    """Load market fixture for respx mocking."""
    return load_golden_response("market_single_response.json")

def load_markets_list_fixture() -> dict[str, Any]:
    """Load markets list fixture."""
    return load_golden_response("markets_list_response.json")

def load_orderbook_fixture() -> dict[str, Any]:
    """Load orderbook fixture."""
    return load_golden_response("orderbook_response.json")
```

#### Step 2: Refactor `test_market.py` pattern

**Before (wrong):**
```python
@patch("kalshi_research.api.KalshiPublicClient")
def test_market_get(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client_cls.return_value = mock_client

    mock_market = MagicMock()
    mock_market.ticker = "TEST-MARKET"
    # ... 15 more MagicMock attribute assignments
    mock_client.get_market.return_value = mock_market

    result = runner.invoke(app, ["market", "get", "TEST-MARKET"])
    assert result.exit_code == 0
```

**After (correct):**
```python
from tests.unit.cli.fixtures import load_market_fixture

@pytest.mark.asyncio
@respx.mock
def test_market_get() -> None:
    fixture = load_market_fixture()
    ticker = fixture["market"]["ticker"]

    respx.get(f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}").mock(
        return_value=Response(200, json=fixture)
    )

    result = runner.invoke(app, ["market", "get", ticker])

    assert result.exit_code == 0
    assert ticker in result.stdout
    # CLI now parses REAL Market model from golden fixture
```

#### Step 3: Handle async context in Typer CLI tests

**Challenge:** Typer's `CliRunner` is synchronous, but our client uses `async with`.

**Solution:** The CLI commands already handle async internally via `asyncio.run()` or similar patterns. The `respx.mock` decorator works at the `httpx` level, which is called regardless of sync/async wrapper.

```python
# This works because respx intercepts httpx requests at transport level
@respx.mock
def test_market_get() -> None:
    respx.get(...).mock(return_value=Response(200, json=fixture))
    result = runner.invoke(app, ["market", "get", "TICKER"])
    # respx intercepts the httpx call inside the async context
```

#### Step 4: Portfolio tests - dual mocking (HTTP + DB)

Portfolio tests need both HTTP mocking (for `portfolio sync`) AND DB mocking (for `portfolio positions`).

```python
# tests/unit/cli/test_portfolio.py refactor pattern
@respx.mock
def test_portfolio_sync_and_positions() -> None:
    # Mock Kalshi API at HTTP boundary
    respx.get(".../portfolio/balance").mock(
        return_value=Response(200, json=load_golden_response("portfolio_balance_response.json"))
    )
    respx.get(".../portfolio/positions").mock(
        return_value=Response(200, json=load_golden_response("portfolio_positions_response.json"))
    )

    # For DB, still use patch but with real SQLite or mock at session level
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["portfolio", "sync"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["portfolio", "positions"])
        assert result.exit_code == 0
```

### Acceptance Criteria (Phase 4)

- [ ] Create `tests/unit/cli/fixtures.py` with golden fixture loaders
- [ ] Refactor `test_market.py` to use `@respx.mock` + golden fixtures
- [ ] Refactor `test_portfolio.py` to use `@respx.mock` for API calls
- [ ] Refactor `test_scan.py` to use `@respx.mock`
- [ ] Remove all `MagicMock()` market/order/position returns from CLI tests
- [ ] All CLI tests still pass with real Pydantic model parsing
- [ ] Add smoke test: break a model field, verify CLI test fails

**Effort:** Medium-High (refactor ~50 tests across 5 files)

---

## Acceptance Criteria

### Phase 1: Exa SSOT (P1)
- [x] Create `tests/fixtures/golden/exa/` directory
- [x] Record Exa golden fixtures for: `/search`, `/contents`, `/findSimilar`, `/answer`, `/research/v1`
- [x] Add Exa models to `validate_models_against_golden.py`
- [x] All Exa models pass validation

### Phase 2: Fix Test Drift (P1)
- [x] Refactor `tests/unit/api/test_trading.py` to load golden order responses (create/cancel/amend) instead of inline dicts
- [x] Refactor `tests/unit/api/test_client_extended.py` to use golden fixtures for portfolio endpoints instead of minimal JSON
- [x] Update `tests/conftest.py:make_market()` to be fixture-shaped (base from `market_single_response.json`, then allow overrides)
- [ ] Optional: add a CI-only check that flags "inline mock drift" (missing keys vs golden), without forcing every unit test to use fixtures

#### Phase 2 Implementation Notes (SSOT)

- **Trading fixtures to use** (recorded + sanitized): `create_order_response.json`, `cancel_order_response.json`, `amend_order_response.json`.
- **Portfolio fixtures to use** (recorded + sanitized): `portfolio_balance_response.json`, `portfolio_positions_response.json`, `portfolio_orders_response.json`, `portfolio_fills_response.json`, `portfolio_settlements_response.json`.
- Prefer assertions of the form "returned model equals fixture values" (read expected values from the fixture) instead of hard-coded numbers.
- Keep "negative tests" (e.g., legacy keys, error handling) as intentionally-minimal mocks; Phase 2 targets only the **happy-path** drift risk.
- **Verified (2026-01-12):** `tests/conftest.py:make_orderbook()` and `make_trade()` are currently unused in the test suite (per `rg`). They are not required for Phase 2.

#### Phase 2 Optional: Inline Mock Drift Guard (CI-only)

**Goal:** Catch when test mocks diverge from golden fixtures without forcing every test to load fixtures.

**Implementation approach:**

```python
# scripts/check_mock_drift.py (NEW)
"""
CI-only script to detect inline mock drift.

Scans test files for inline dict mocks and compares keys against golden fixtures.
Warns (not fails) when inline mocks are missing required fields.
"""

import ast
import json
from pathlib import Path

GOLDEN_DIR = Path("tests/fixtures/golden")
REQUIRED_FIELDS = {
    "market": ["ticker", "status", "yes_bid", "yes_ask", "no_bid", "no_ask"],
    "order": ["order_id", "status", "action", "side", "type"],
    "position": ["ticker", "side", "quantity"],
}

def extract_inline_dicts(filepath: Path) -> list[dict]:
    """Parse Python AST to find inline dict literals in test files."""
    # ... AST walking logic
    pass

def compare_to_golden(inline_dict: dict, model_type: str) -> list[str]:
    """Return list of missing required fields."""
    required = REQUIRED_FIELDS.get(model_type, [])
    return [f for f in required if f not in inline_dict]
```

**CI integration:**
```yaml
# .github/workflows/ci.yml (add to lint job)
- name: Check inline mock drift (warning only)
  run: uv run python scripts/check_mock_drift.py --warn-only
  continue-on-error: true  # Don't fail CI, just warn
```

**Why optional:** This is a nice-to-have guard, but the real fix is Phase 4 (mock at HTTP boundary). If Phase 4 is completed, this becomes unnecessary.

### Phase 3: Close Kalshi Gaps (P2)
- [x] Record trades golden fixture (e.g., `trades_list_response.json`)
- [x] Add `test_get_event_single` test
- [x] Record `candlesticks_batch_response.json` and add test for `get_candlesticks()`
- [x] Record `series_candlesticks_response.json` and add test

### Phase 4: CLI Test Architecture (P3)
- [x] Create `tests/unit/cli/fixtures.py` with golden fixture loaders
- [x] Refactor `test_market.py` to use `@respx.mock` + real API-shaped JSON
- [x] Refactor `test_portfolio.py` to use `@respx.mock` for API calls (`portfolio balance`)
- [x] Refactor `test_scan.py` to use `@respx.mock` + real API-shaped JSON
- [x] Remove `MagicMock()` *market* returns from the Phase 4 CLI tests
- [x] All Phase 4 CLI tests still pass with real Pydantic model parsing
- [x] Add smoke test: intentionally break a required field and assert the CLI fails

---

## Implementation Order

```
DEBT-018 Phase 4 (CLI Tests) - lower priority (remaining)
    ↓
DEBT-016 (CI Automation) - builds on SSOT baseline
    ↓
DEBT-017 (Model cleanup) - optional follow-up
    ↓
DEBT-015 (Missing Endpoints) - only after foundation solid
```

---

## Known Risks (Accepted)

These are known limitations that are accepted as reasonable risk:

### 1. `series_fee_changes_response.json` has empty array

**Fixture:**
```json
{
  "_metadata": { "endpoint": "series_fee_changes", ... },
  "response": { "series_fee_change_arr": [] }
}
```

**Risk:** The `SeriesFeeChange` model fields are NOT validated against real data. Only the wrapper response (`SeriesFeeChangesResponse`) is validated.

**Why accepted:** We cannot manufacture fee changes. The Kalshi API returned an empty array when recorded. The wrapper validates correctly, and the inner model schema matches the OpenAPI spec.

**Mitigation:** Re-record this fixture when a real fee change exists. Add a TODO comment in the validation script:

```python
# TODO: Re-record series_fee_changes_response.json when non-empty data available
# Currently validates wrapper only, not SeriesFeeChange fields
```

### 2. Exa fixture URLs use placeholder domains

**Fixture:** `tests/fixtures/golden/exa/*.json` use `example.com`, `eexample.com`, etc.

**Risk:** The URLs in Exa fixtures are not real production URLs.

**Why accepted:** Exa returns real search results which may contain sensitive/PII data. Using placeholder domains is intentional sanitization. The model structure (not URL values) is what we validate.

---

## Cross-References

| Item | Relationship |
|------|--------------|
| DEBT-016 | CI automation for fixture drift (builds on this) |
| DEBT-017 | Duplicate Order models (separate issue) |
| DEBT-015 | Missing API endpoints (do AFTER this debt) |
| BUG-071 | Original mocked tests finding (now archived) |
| `scripts/validate_models_against_golden.py` | Existing validation script to extend |
| `scripts/record_api_responses.py` | Existing recording script to extend |

---

## Why This Matters

**Without this debt paid:**
- Adding new features risks silent regressions
- Exa API changes will break production without warning
- Tests give false confidence (pass with wrong data)
- Other agents working on codebase may introduce drift

**With this debt paid:**
- Golden fixtures are SSOT for all external APIs (Kalshi + Exa)
- Tests validate against reality, not imagination
- CI catches drift before it hits production
- Safe foundation for DEBT-015 (new endpoints) and new features
