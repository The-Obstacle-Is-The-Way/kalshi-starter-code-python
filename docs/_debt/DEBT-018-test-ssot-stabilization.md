# DEBT-018: Test SSOT Stabilization (Fixtures, Mocks, Exa Coverage)

**Priority:** P1 (Foundation stability before new features)
**Status:** Open
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
# tests/unit/cli/test_market.py
@patch("kalshi_research.api.KalshiPublicClient")
def test_market_get(mock_client_cls: MagicMock) -> None:
    mock_market = MagicMock()
    mock_market.status.value = "active"  # MagicMock, not real enum
```

### Issue

- Mocks entire client class, not HTTP boundary
- Returns `MagicMock` objects, not real Pydantic models
- Model validation errors won't be caught
- Tests don't verify CLI actually parses real API responses correctly

### Recommended Fix

Refactor CLI tests to:
1. Mock at HTTP boundary (respx)
2. Use real Pydantic models in responses
3. Let CLI code parse models naturally

**Effort:** Medium (refactor ~5 CLI test files)

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
- [ ] Optional: add a CI-only check that flags “inline mock drift” (missing keys vs golden), without forcing every unit test to use fixtures

#### Phase 2 Implementation Notes (SSOT)

- **Trading fixtures to use** (recorded + sanitized): `create_order_response.json`, `cancel_order_response.json`, `amend_order_response.json`.
- **Portfolio fixtures to use** (recorded + sanitized): `portfolio_balance_response.json`, `portfolio_positions_response.json`, `portfolio_orders_response.json`, `portfolio_fills_response.json`, `portfolio_settlements_response.json`.
- Prefer assertions of the form “returned model equals fixture values” (read expected values from the fixture) instead of hard-coded numbers.
- Keep “negative tests” (e.g., legacy keys, error handling) as intentionally-minimal mocks; Phase 2 targets only the **happy-path** drift risk.
- **Verified (2026-01-12):** `tests/conftest.py:make_orderbook()` and `make_trade()` are currently unused in the test suite (per `rg`). They are not required for Phase 2.

### Phase 3: Close Kalshi Gaps (P2)
- [x] Record trades golden fixture (e.g., `trades_list_response.json`)
- [x] Add `test_get_event_single` test
- [x] Record `candlesticks_batch_response.json` and add test for `get_candlesticks()`
- [x] Record `series_candlesticks_response.json` and add test

### Phase 4: CLI Test Architecture (P3)
- [ ] Refactor `test_market.py` to mock HTTP, not client
- [ ] Refactor `test_portfolio.py` similarly
- [ ] All CLI tests use real Pydantic models

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
