# BUG-071 Appendix: Complete Mock Audit

**Generated:** 2026-01-12
**Related:** [BUG-071-mocked-tests-hide-api-reality.md](BUG-071-mocked-tests-hide-api-reality.md)

---

## Executive Summary

- **Total Test Files Analyzed**: 65+ files
- **Total Mocks Identified**: 200+
- **HIGH Risk Mocks**: 15 (API response shape - schema drift hazard)
- **MEDIUM Risk Mocks**: 45 (External state/behavior)
- **LOW Risk Mocks**: 140+ (Internal implementation - acceptable)

---

## HIGH RISK MOCKS (API Response Shape - Schema Drift Hazard)

These mocks are **CRITICAL** because they define the exact shape of API responses. If Kalshi API changes, these tests will NOT catch it.

| File | Line | Mock Target | Mocked Value | Notes |
|------|------|-------------|--------------|-------|
| `tests/unit/api/test_client.py` | 24-47 | Market API Response | Dict with market fields | Mock fixture defines API contract |
| `tests/unit/api/test_client.py` | 54-67 | GET /markets/{ticker} | 200 + market dict | respx mock |
| `tests/unit/api/test_client.py` | 127-155 | GET /markets (paginated) | Two-page response | Pagination structure assumed |
| `tests/unit/api/test_client.py` | 346-366 | GET /orderbook | `[[price, qty], ...]` arrays | Array format hardcoded |
| `tests/unit/api/test_client.py` | 369-396 | GET /trades | Trade objects | Field names not validated |
| `tests/unit/api/test_client.py` | 415-452 | GET /candlesticks | OHLC structure | Deep nested structure |
| `tests/unit/api/test_client.py` | 468-492 | GET /events | Event objects | Event schema mocked |
| `tests/unit/api/test_trading.py` | 12-26 | KalshiClient fixture | Mocked HTTP + auth | Entire client mocked |
| `tests/unit/api/test_trading.py` | 32-35 | POST /portfolio/orders | `{"order": {"order_id": "...", "status": "..."}}` | **Order response hardcoded** |
| `tests/unit/data/test_fetcher.py` | 96-101 | Event model | MagicMock | Real model skipped |
| `tests/unit/data/test_fetcher.py` | 123-134 | Market model | MagicMock | Real model skipped |
| `tests/integration/api/test_client_error_handling.py` | 17-26 | Exchange status | `{"exchange_active": true}` | respx mock |
| `tests/integration/api/test_client_error_handling.py` | 58-69 | 429 Rate Limit | Retry sequence mocked | Headers not validated |
| `tests/unit/api/test_models.py` | 90-132 | Market dollar fields | Optional fields assumed | Real API contract unknown |
| `tests/unit/api/test_models.py` | 134-187 | Market structural fields | OpenAPI fields | All optional in test |

---

## MEDIUM RISK MOCKS (External State/Behavior)

| File | Line | Mock Target | Notes |
|------|------|-------------|-------|
| `tests/unit/api/test_client.py` | 117-124 | asyncio.sleep | Rate limit timing mocked |
| `tests/unit/api/test_client.py` | 521-526 | Rate limiter acquire | Never actually throttles |
| `tests/unit/api/test_client.py` | 575-596 | KalshiAuth + HTTP | Auth flow never validated |
| `tests/unit/exa/test_client.py` | 29-60 | Exa API search | Exa contract mocked |
| `tests/unit/exa/test_client.py` | 129-141 | Exa rate limit | Retry-after header mocked |
| `tests/unit/data/test_fetcher.py` | 108-117 | EventRepository | AsyncMock upsert |
| `tests/unit/data/test_fetcher.py` | 144-157 | MarketRepository | AsyncMock upsert |
| `tests/unit/data/test_fetcher.py` | 185-207 | SettlementRepository | AsyncMock |
| `tests/unit/data/test_fetcher.py` | 241-249 | PriceRepository | Snapshot persistence mocked |
| `tests/unit/portfolio/test_syncer.py` | 28-54 | DatabaseManager | Session mocked |
| `tests/unit/portfolio/test_syncer.py` | 62-108 | get_positions | Position list returned directly |
| `tests/unit/portfolio/test_syncer.py` | 182-227 | get_fills pagination | FillPage cursor mocked |
| `tests/unit/api/test_rate_limiter.py` | 90-99 | TokenBucket.acquire | Side effect mocked |
| `tests/unit/cli/test_data.py` | 16-28 | DatabaseManager | AsyncMock |
| `tests/unit/cli/test_data.py` | 31-52 | DataFetcher | AsyncMock sync methods |
| `tests/unit/cli/test_portfolio.py` | 47-76 | KalshiClient | AsyncMock get_balance |
| `tests/unit/execution/test_executor.py` | 22-51 | TradeExecutor | OrderResponse mocked |
| `tests/unit/data/test_export.py` | 8-19 | duckdb.connect | MagicMock connection |

---

## LOW RISK MOCKS (Acceptable)

These follow best practices - mocking at boundaries or using real objects.

| File | Pattern | Notes |
|------|---------|-------|
| `tests/conftest.py` | Real in-memory SQLite | **Excellent** |
| `tests/conftest.py` | make_market/make_orderbook factories | Test data helpers |
| `tests/unit/api/test_models.py` | Real Pydantic models | **Excellent** |
| `tests/unit/data/test_repositories.py` | Real SQLite session | **Gold standard** |
| `tests/unit/alerts/test_monitor.py` | Real Market objects | Good |
| `tests/unit/research/test_thesis.py` | Real Thesis dataclass | Good |

---

## CRITICAL SAFETY ISSUES

### Issue #1: API Response Shape Not Validated
**Severity: P0**

Mocked responses are hardcoded dicts never validated against OpenAPI or real API.

```python
# BAD: Hardcoded dict that may not match reality
mock_response = {"order": {"order_id": "...", "status": "resting"}}
```

### Issue #2: Repository Pattern Defeated by Mocks
**Severity: P1**

`test_fetcher.py` mocks repositories instead of using real DB:
```python
# BAD: Mocks the repository
with patch("...EventRepository") as MockRepo:
    mock_repo = AsyncMock()
```

### Issue #3: Authenticated Client Never Tested E2E
**Severity: P1**

Order creation (financial risk) only tested with mocked HTTP.

### Issue #4: Portfolio Syncer Mocks Transactions
**Severity: P1**

Session mocked - transaction safety never tested.

### Issue #5: Rate Limiter Never Actually Rate-Limits
**Severity: P2**

TokenBucket mocked - real throttling never tested.

---

## MOCK TESTING PHILOSOPHY

**Rule: Mock at system boundaries, use real objects everywhere else.**

### ✅ GOOD: HTTP Boundary Mock
```python
@respx.mock
async def test_get_market():
    respx.get("...").mock(return_value=Response(200, json=GOLDEN_RESPONSE))
```

### ✅ GOOD: Real Database
```python
async def test_repository(async_session):
    repo = EventRepository(async_session)  # Real in-memory SQLite
    await repo.add(event)
```

### ❌ BAD: Mocking Domain Logic
```python
@patch("kalshi_research.data.fetcher.EventRepository")
async def test_sync():
    mock_repo = AsyncMock()  # Should use real repo
```

### ❌ BAD: Hardcoded Response Without Validation
```python
mock_response = {"order": {"status": "resting"}}  # Is this what API sends?
```

---

## FILES REQUIRING ATTENTION (Priority Order)

| File | Risk | Issue |
|------|------|-------|
| `tests/unit/api/test_trading.py` | **HIGH** | Order creation mocked - financial risk |
| `tests/unit/api/test_client.py` | **HIGH** | 30+ API response mocks |
| `tests/unit/data/test_fetcher.py` | **HIGH** | Repository mocks defeat DB testing |
| `tests/unit/portfolio/test_syncer.py` | **HIGH** | Transaction safety mocked |
| `tests/integration/api/test_client_error_handling.py` | **MEDIUM** | Error responses assumed |

---

## NEXT STEPS

1. **Record golden fixtures** from demo API for each HIGH risk endpoint
2. **Validate mocks** against golden fixtures using `model_validate()`
3. **Convert repository mocks** to real in-memory SQLite
4. **Add E2E auth test** against demo API with dry-run orders
5. **Document mock policy** in CLAUDE.md
