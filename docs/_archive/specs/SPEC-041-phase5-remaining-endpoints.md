# SPEC-041: Phase 5 - Remaining High-Value Endpoints

**Status:** ✅ Implemented (Multivariate collections subset)
**Priority:** P2 (Complete personal system)
**Created:** 2026-01-15
**Owner:** Solo
**Depends On:** [SPEC-040](../_archive/specs/SPEC-040-kalshi-endpoint-implementation-complete.md) (Complete)
**Effort:** ~1 day

---

## Executive Summary

Phase 5 implements the remaining **high-value endpoints that are actually usable today** for a solo trader research
system. This currently means **Multivariate Event Collections** (combo-market discovery/lookup).

During fixture recording we found **API drift / permission blocks** for Subaccounts and Forecast Percentile History
(documented below). Until Kalshi enables these endpoints for our accounts, they are treated as **blocked** and are
not part of the implementation set.

**NOT implementing (after Phase 5):**
- RFQ/Communications (institutional) - 11 endpoints
- API Keys (security risk) - 4 endpoints
- FCM (institutional) - 2 endpoints
- Multivariate Collections: create market + lookup history - 2 endpoints
- Subaccounts: 4 endpoints (OpenAPI exists, but endpoints are unavailable in practice)
- Forecast percentile history: 1 endpoint (OpenAPI exists; auth + required query params; no validated 200 fixture yet)

---

## Endpoints to Implement

### 1. Multivariate Event Collections (3 endpoints)

**Purpose:** Discover and analyze combo markets across ANY event types (not just sports).

**SSOT (OpenAPI):** `https://docs.kalshi.com/openapi.yaml` (verified 2026-01-15)

| Endpoint | Auth | Client | Method Name | Use Case |
|----------|------|--------|-------------|----------|
| `GET /multivariate_event_collections` | No | `KalshiPublicClient` | `get_multivariate_event_collections()` | List available collection templates (with filters + pagination) |
| `GET /multivariate_event_collections/{collection_ticker}` | No (OpenAPI; verified via unauthenticated `curl`) | `KalshiPublicClient` | `get_multivariate_event_collection()` | Get collection details |
| `PUT /multivariate_event_collections/{collection_ticker}/lookup` | Yes | `KalshiClient` | `lookup_multivariate_event_collection_tickers()` | Resolve selected markets → produced market ticker |

**Not implemented in Phase 5 (OpenAPI exists, low value for solo tool):**
- `POST /multivariate_event_collections/{collection_ticker}` (auth) - create market in collection
- `GET /multivariate_event_collections/{collection_ticker}/lookup` (no auth) - lookup **history** (requires `lookback_seconds`)

**List endpoint filters (OpenAPI):**
- `status`: `unopened|open|closed`
- `associated_event_ticker`: `str`
- `series_ticker`: `str`
- `limit`: `int` (1-200)
- `cursor`: `str`

**Why valuable:**
- Find correlated event combos: "Fed raises AND inflation stays high"
- Discover non-obvious parlay opportunities across economics, politics, crypto
- Edge discovery tool - find bets others aren't looking at

**Models needed (OpenAPI exact field names):**
```python
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class MultivariateAssociatedEvent(BaseModel):
    """Associated event constraints inside a multivariate event collection."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    is_yes_only: bool
    size_max: int | None = None
    size_min: int | None = None
    active_quoters: list[str]


class MultivariateEventCollection(BaseModel):
    """Multivariate event collection ('multivariate_contract' in OpenAPI)."""

    model_config = ConfigDict(frozen=True)

    collection_ticker: str
    series_ticker: str
    title: str
    description: str
    open_date: datetime
    close_date: datetime
    associated_events: list[MultivariateAssociatedEvent]
    associated_event_tickers: list[str]
    is_ordered: bool
    is_single_market_per_event: bool
    is_all_yes: bool
    size_min: int
    size_max: int
    functional_description: str


class GetMultivariateEventCollectionsResponse(BaseModel):
    """Response wrapper for GET /multivariate_event_collections."""

    model_config = ConfigDict(frozen=True)

    multivariate_contracts: list[MultivariateEventCollection]
    cursor: str | None = None


class GetMultivariateEventCollectionResponse(BaseModel):
    """Response wrapper for GET /multivariate_event_collections/{collection_ticker}."""

    model_config = ConfigDict(frozen=True)

    multivariate_contract: MultivariateEventCollection


class TickerPair(BaseModel):
    """Selected market input for multivariate lookup/create endpoints."""

    model_config = ConfigDict(frozen=True)

    market_ticker: str
    event_ticker: str
    side: Literal["yes", "no"]


class LookupTickersForMarketInMultivariateEventCollectionRequest(BaseModel):
    """Request body for PUT /multivariate_event_collections/{collection_ticker}/lookup."""

    model_config = ConfigDict(frozen=True)

    selected_markets: list[TickerPair]


class LookupTickersForMarketInMultivariateEventCollectionResponse(BaseModel):
    """Response for PUT /multivariate_event_collections/{collection_ticker}/lookup."""

    model_config = ConfigDict(frozen=True)

    event_ticker: str
    market_ticker: str
```

### 2. Subaccounts (4 endpoints)

**Purpose:** Capital segmentation for strategy isolation and performance tracking.

**SSOT (observed 2026-01-15): API blocked / unavailable**

These endpoints appear in `openapi.yaml`, but are not usable with our current accounts/environments:

- **Demo**:
  - `POST /portfolio/subaccounts` → `404 page not found`
  - `POST /portfolio/subaccounts/transfer` → `404 page not found`
  - `GET /portfolio/subaccounts/balances` → `200` with empty `subaccount_balances: []`
  - `GET /portfolio/subaccounts/transfers` → `200` with empty `transfers: []`
- **Prod**:
  - `POST /portfolio/subaccounts` → `404 page not found`
  - `POST /portfolio/subaccounts/transfer` → `404 page not found`
  - `GET /portfolio/subaccounts/balances` → `403 invalid_parameters` (`details`: “subaccount endpoints are not available in production”)
  - `GET /portfolio/subaccounts/transfers` → `403 invalid_parameters` (`details`: “subaccount endpoints are not available in production”)

**Verdict:** Blocked by Kalshi API availability/permissions. Do not implement until we can record stable fixtures without
side effects.

| Endpoint | Auth | Method Name | Use Case |
|----------|------|-------------|----------|
| `POST /portfolio/subaccounts` | Yes | `create_subaccount()` | Create new numbered subaccount |
| `GET /portfolio/subaccounts/balances` | Yes | `get_subaccount_balances()` | View balances across all subaccounts |
| `POST /portfolio/subaccounts/transfer` | Yes | `transfer_between_subaccounts()` | Move funds between accounts |
| `GET /portfolio/subaccounts/transfers` | Yes | `get_subaccount_transfers()` | Transfer history |

**Changelog note:** The Jan 9, 2026 changelog lists only the 4 endpoints above; no additional subaccount endpoints are
listed there.

**Why valuable:**
- Track "Macro Thesis" vs "Crypto Thesis" separately
- Know which strategies are actually profitable
- Proper capital allocation across approaches
- Professional trading practice

**Models needed (OpenAPI exact field names):**
```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CreateSubaccountResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    subaccount_number: int  # 1-32 (primary is 0)


class SubaccountBalance(BaseModel):
    model_config = ConfigDict(frozen=True)

    subaccount_number: int
    balance: int
    updated_ts: int


class GetSubaccountBalancesResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    subaccount_balances: list[SubaccountBalance]


class ApplySubaccountTransferRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    from_subaccount: int
    to_subaccount: int
    amount_cents: int


class ApplySubaccountTransferResponse(BaseModel):
    """Empty response for POST /portfolio/subaccounts/transfer."""

    model_config = ConfigDict(frozen=True)


class SubaccountTransfer(BaseModel):
    model_config = ConfigDict(frozen=True)

    transfer_id: str
    from_subaccount: int
    to_subaccount: int
    amount: int
    created_ts: int


class GetSubaccountTransfersResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    transfers: list[SubaccountTransfer]
    cursor: str | None = None
```

### 3. Forecast Percentile History (1 endpoint)

**Purpose:** Historical forecast accuracy for calibration research.

| Endpoint | Auth | Method Name | Use Case |
|----------|------|-------------|----------|
| `GET /series/{series_ticker}/events/{ticker}/forecast_percentile_history` | Yes (OpenAPI) | `get_forecast_percentile_history()` | Historical forecast percentiles |

**Request parameters (all required, OpenAPI):**
- `percentiles`: `list[int]` (0-10000, max 10 items)
- `start_ts`: `int`
- `end_ts`: `int`
- `period_interval`: `0|1|60|1440`

**Changelog note (not in OpenAPI as of 2026-01-15):**
- Older changelog entry references `GET /forecast_percentiles_history` (no series/event path). This endpoint is not
  present in `openapi.yaml`; implement the series/event-scoped endpoint above.

**Why valuable:**
- See how accurate Kalshi's crowd has been historically
- Know when to fade vs follow the crowd
- Calibration edge - crowds are often wrong at extremes

**Models needed (OpenAPI exact field names):**
```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ForecastPercentilePoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    percentile: int  # 0-10000
    raw_numerical_forecast: float
    numerical_forecast: float
    formatted_forecast: str


class ForecastPercentileHistoryEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_ticker: str
    end_period_ts: int
    period_interval: int
    percentile_points: list[ForecastPercentilePoint]


class GetEventForecastPercentilesHistoryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    forecast_history: list[ForecastPercentileHistoryEntry]
```

**Status (2026-01-16):** Not implemented. OpenAPI requires `percentiles`, `start_ts`, `end_ts`, and `period_interval`.
Until we can record a stable `200` fixture with valid parameters, treat this endpoint as unimplemented.

---

## Implementation Plan

### Step 1: Record Golden Fixtures ✅

```bash
# Add to scripts/record_api_responses.py
# Multivariate Collections (public)
GET /multivariate_event_collections
GET /multivariate_event_collections/{collection_ticker}

# Multivariate Collections (auth)
PUT /multivariate_event_collections/{collection_ticker}/lookup

# Subaccounts + Forecast History are blocked (see above).
```

### Step 2: Create Pydantic Models ✅

New files:
- `src/kalshi_research/api/models/multivariate.py`

### Step 3: Implement Client Methods ✅

Add to `src/kalshi_research/api/client.py`:

**KalshiPublicClient:**
- `get_multivariate_event_collections()`
- `get_multivariate_event_collection()`

**KalshiClient (auth):**
- `lookup_multivariate_event_collection_tickers()`

### Step 4: Add Tests ✅

New test file:
- `tests/unit/api/test_client_phase5.py`

### Step 5: Optional CLI Commands (Deferred / API-blocked)

Consider adding later, only if/when Kalshi enables the underlying endpoints:
- `kalshi portfolio subaccounts` - List subaccount balances (subaccounts API blocked)
- `kalshi research forecast-history TICKER` - Show forecast accuracy (forecast history API blocked)

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
| 47/74 (64%) | 50/74 (68%) | +3 endpoints |

**Remaining unimplemented (19 endpoints):**
- RFQ/Communications: 11 (institutional)
- API Keys: 4 (security risk)
- FCM: 2 (institutional)
- Multivariate Collections (not planned): 2 (create market, lookup history)

**API-blocked (do not implement yet):**
- Subaccounts: 4 (OpenAPI exists, but endpoints are unavailable in demo/prod for our accounts)
- Forecast percentile history: 1 (OpenAPI exists, but returned 400 for all tested events)

These are intentionally not implemented - they don't apply to solo retail trading.

---

## Cross-References

| Item | Relationship |
|------|--------------|
| SPEC-040 | Phases 1-4 (prerequisite, complete) |
| DEBT-015 | Phase 5 decision matrix |
| `kalshi-openapi-coverage.md` | Update after implementation |
