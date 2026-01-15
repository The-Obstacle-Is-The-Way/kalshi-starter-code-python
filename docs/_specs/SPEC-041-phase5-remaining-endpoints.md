# SPEC-041: Phase 5 - Remaining High-Value Endpoints

**Status:** 📝 Ready for Implementation
**Priority:** P2 (Complete personal system)
**Created:** 2026-01-15
**Owner:** Solo
**Depends On:** SPEC-040 (Complete)
**Effort:** ~1 day

---

## Executive Summary

Phase 5 completes the Kalshi API client with 8 remaining high-value endpoints for a solo trader research system. This takes coverage from 64% to 74%.

**NOT implementing:** RFQ (institutional), API Keys (security risk), FCM (institutional) - 17 endpoints that don't apply to solo retail trading.

---

## Endpoints to Implement

### 1. Multivariate Event Collections (3 endpoints)

**Purpose:** Discover and analyze combo markets across ANY event types (not just sports).

| Endpoint | Auth | Method Name | Use Case |
|----------|------|-------------|----------|
| `GET /multivariate_event_collections` | No | `get_multivariate_collections()` | List all available combo market templates |
| `GET /multivariate_event_collections/{ticker}` | Yes | `get_multivariate_collection()` | Get details of a specific collection |
| `GET /multivariate_event_collections/{ticker}/lookup` | Yes | `lookup_multivariate_collection()` | Map variable combinations to tickers |

**Why valuable:**
- Find correlated event combos: "Fed raises AND inflation stays high"
- Discover non-obvious parlay opportunities across economics, politics, crypto
- Edge discovery tool - find bets others aren't looking at

**Models needed:**
```python
class MultivariateEventCollection(BaseModel):
    collection_ticker: str
    title: str
    # ... TBD from fixture

class MultivariateCollectionLookup(BaseModel):
    market_ticker: str
    # ... TBD from fixture
```

### 2. Subaccounts (4 endpoints)

**Purpose:** Capital segmentation for strategy isolation and performance tracking.

| Endpoint | Auth | Method Name | Use Case |
|----------|------|-------------|----------|
| `POST /portfolio/subaccounts` | Yes | `create_subaccount()` | Create new subaccount (up to 32) |
| `GET /portfolio/subaccounts/balances` | Yes | `get_subaccount_balances()` | View balances across all subaccounts |
| `POST /portfolio/subaccounts/transfer` | Yes | `transfer_between_subaccounts()` | Move funds between accounts |
| `GET /portfolio/subaccounts/transfers` | Yes | `get_subaccount_transfers()` | Transfer history |

**Why valuable:**
- Track "Macro Thesis" vs "Crypto Thesis" separately
- Know which strategies are actually profitable
- Proper capital allocation across approaches
- Professional trading practice

**Models needed:**
```python
class SubaccountBalance(BaseModel):
    subaccount_id: int  # 0-32
    balance: int
    portfolio_value: int

class SubaccountTransfer(BaseModel):
    transfer_id: str
    from_subaccount: int
    to_subaccount: int
    amount: int
    created_time: str
```

### 3. Forecast Percentile History (1 endpoint)

**Purpose:** Historical forecast accuracy for calibration research.

| Endpoint | Auth | Method Name | Use Case |
|----------|------|-------------|----------|
| `GET /series/{s}/events/{e}/forecast_percentile_history` | Yes | `get_forecast_history()` | Historical forecast percentiles |

**Why valuable:**
- See how accurate Kalshi's crowd has been historically
- Know when to fade vs follow the crowd
- Calibration edge - crowds are often wrong at extremes

**Models needed:**
```python
class ForecastPercentile(BaseModel):
    timestamp: str
    percentile: float
    # ... TBD from fixture
```

---

## Implementation Plan

### Step 1: Record Golden Fixtures

```bash
# Add to scripts/record_api_responses.py
# Multivariate Collections (public)
GET /multivariate_event_collections

# Multivariate Collections (auth) - need demo creds
GET /multivariate_event_collections/{collection_ticker}
GET /multivariate_event_collections/{collection_ticker}/lookup

# Subaccounts (auth)
POST /portfolio/subaccounts
GET /portfolio/subaccounts/balances
POST /portfolio/subaccounts/transfer
GET /portfolio/subaccounts/transfers

# Forecast History (auth)
GET /series/{series_ticker}/events/{event_ticker}/forecast_percentile_history
```

### Step 2: Create Pydantic Models

New files:
- `src/kalshi_research/api/models/multivariate.py`
- `src/kalshi_research/api/models/subaccount.py`

Add to existing:
- `src/kalshi_research/api/models/event.py` (forecast history)

### Step 3: Implement Client Methods

Add to `src/kalshi_research/api/client.py`:

**KalshiPublicClient:**
- `get_multivariate_collections()`

**KalshiClient (auth):**
- `get_multivariate_collection()`
- `lookup_multivariate_collection()`
- `create_subaccount()`
- `get_subaccount_balances()`
- `transfer_between_subaccounts()`
- `get_subaccount_transfers()`
- `get_forecast_history()`

### Step 4: Add Tests

New test file:
- `tests/unit/api/test_client_phase5.py`

### Step 5: Optional CLI Commands

Consider adding later:
- `kalshi portfolio subaccounts` - List subaccount balances
- `kalshi research forecast-history TICKER` - Show forecast accuracy

---

## Verification

```bash
# After implementation
uv run python scripts/validate_models_against_golden.py
uv run pytest tests/unit/api/test_client_phase5.py -v
uv run pre-commit run --all-files
```

---

## Coverage Impact

| Before | After | Change |
|--------|-------|--------|
| 47/74 (64%) | 55/74 (74%) | +8 endpoints |

**Remaining unimplemented (17 endpoints):**
- RFQ/Communications: 11 (institutional)
- API Keys: 4 (security risk)
- FCM: 2 (institutional)

These are intentionally not implemented - they don't apply to solo retail trading.

---

## Cross-References

| Item | Relationship |
|------|--------------|
| SPEC-040 | Phases 1-4 (prerequisite, complete) |
| DEBT-015 | Phase 5 decision matrix |
| `kalshi-openapi-coverage.md` | Update after implementation |
