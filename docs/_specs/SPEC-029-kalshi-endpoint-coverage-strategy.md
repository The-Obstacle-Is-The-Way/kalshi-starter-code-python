# SPEC-029: Kalshi Endpoint Coverage & Strategic Use

**Status:** Draft
**Priority:** P1 (Data Quality / Discovery)
**Created:** 2026-01-10
**Owner:** Solo
**Effort:** ~1–2 days (Phase 1), ~3–5 days (Phase 2 persistence)

---

## Summary

Expand and formalize our usage of Kalshi’s official REST endpoints so we can:

- reduce wasteful “fetch everything then filter locally” patterns,
- unlock missing platform capabilities (series templates, structured targets, multivariate events),
- expose time-series endpoints (candlesticks, public trades) cleanly in CLI and optionally persist them for
  backtesting.

This spec is “strategic endpoint usage”, not “build more features for fun”: we only add endpoints that map to
clear workflows and can be tested deterministically.

---

## Goals

1. **Complete public-market coverage** for endpoints that matter to research/discovery:
   - `/markets` filters parity (tickers + timestamp filters)
   - `/events/multivariate` (multivariate events are excluded from `/events`)
   - `/series` and `/series/{series_ticker}` (discoverability + metadata)
   - `/structured_targets` (structured browsing / templated market discovery)
2. **Expose time series endpoints via CLI**:
   - `/markets/trades` (public trades)
   - `/markets/candlesticks` (batch OHLC)
   - `/series/{series_ticker}/markets/{ticker}/candlesticks` (already in client)
   - `/series/{series_ticker}/events/{ticker}/candlesticks` (if needed for event-level analysis)
3. Keep code SOLID: pure clients + repositories + deterministic orchestration.
4. Make everything match SSOT:
   - vendor reference in `../_vendor-docs/kalshi-api-reference.md`
   - OpenAPI spec at `https://docs.kalshi.com/openapi.yaml`

---

## Non-Goals

- No WebSocket ingestion (orderbook_delta, etc.) in this spec.
- No trade execution changes (order placement / safety wrappers).
- No “AI analysis” of the resulting data (that belongs in analysis modules/specs).

---

## Current State (SSOT)

### Already implemented in code

`KalshiPublicClient` currently supports:

- Markets: `/markets`, `/markets/{ticker}`, `/markets/{ticker}/orderbook`
- Trades: `/markets/trades`
- Candlesticks: `/markets/candlesticks`, `/series/{series_ticker}/markets/{ticker}/candlesticks`
- Events: `/events`, `/events/{event_ticker}`
- Exchange: `/exchange/status`

SSOT: `src/kalshi_research/api/client.py`

### Gaps vs vendor docs / OpenAPI

1. **`GET /markets` filter parity**
   - Vendor docs list `tickers`, and timestamp filters `min_*_ts` / `max_*_ts`
     (SSOT: `../_vendor-docs/kalshi-api-reference.md`).
   - OpenAPI confirms compatible timestamp filter sets and that `tickers` is supported
     (SSOT: `https://docs.kalshi.com/openapi.yaml`).
   - Our client currently does **not** expose `tickers` or any `min_*_ts` / `max_*_ts` params.

2. **Multivariate events**
   - Kalshi removed multivariate events from `GET /events`; they are served by `GET /events/multivariate`
     (SSOT: `../_vendor-docs/kalshi-api-reference.md`).
   - Our `DataFetcher.sync_events()` calls only `GET /events`, so DB event coverage is incomplete for MVE.
     (SSOT: `src/kalshi_research/data/fetcher.py`).

3. **Series templates**
   - OpenAPI exposes:
     - `GET /series` with filters (`category`, `tags`, `include_product_metadata`, `include_volume`)
     - `GET /series/{series_ticker}` with `include_volume`
     (SSOT: `https://docs.kalshi.com/openapi.yaml`).
   - We do not implement `/series` list or `/series/{series_ticker}` detail.

4. **Structured targets**
   - OpenAPI exposes:
     - `GET /structured_targets` (filters: `type`, `competition`, pagination via `page_size`, `cursor`)
     - `GET /structured_targets/{structured_target_id}`
     (SSOT: `https://docs.kalshi.com/openapi.yaml`).
   - We do not implement these endpoints.

5. **Time-series endpoints are not wired into CLI/data layer**
   - The client has trades/candlesticks methods, but there is no `kalshi market trades` or `kalshi market
     candlesticks` command.
   - The DB does not persist public trades/candlesticks; only periodic snapshots are stored.

---

## Design

### 1) Expand `GET /markets` filters in `KalshiPublicClient`

Update:

- `KalshiPublicClient.get_markets_page(...)`
- `KalshiPublicClient.get_markets(...)`
- `KalshiPublicClient.get_all_markets(...)`

Add supported filters (all confirmed by OpenAPI and vendor docs):

- `tickers: list[str] | None` → `tickers=...` (comma-separated)
- Timestamp filters (Unix seconds):
  - `min_created_ts`, `max_created_ts`
  - `min_close_ts`, `max_close_ts`
  - `min_settled_ts`, `max_settled_ts`

**Compatibility matrix (OpenAPI)**

Only one timestamp filter family may be used at a time, and it is only compatible with certain status values:

| Timestamp Filters | Compatible `status` |
|---|---|
| `min_created_ts`, `max_created_ts` | `unopened`, `open`, or empty |
| `min_close_ts`, `max_close_ts` | `closed` or empty |
| `min_settled_ts`, `max_settled_ts` | `settled` or empty |

Implementation requirement:
- Validate combinations client-side (raise a helpful `ValueError`) to prevent 400s.

---

### 2) Add missing endpoint families to the API client

#### 2.1 Series endpoints

Add models in `src/kalshi_research/api/models/`:

- `series.py`: `Series`, `SeriesListResponse`, etc. (exact fields taken from OpenAPI schemas)

Add client methods:

- `get_series(series_ticker: str, *, include_volume: bool = False) -> Series`
- `get_series_list_page(..., limit?, cursor?) -> (list[Series], cursor)` (if cursor exists in response)
- `get_all_series(...) -> AsyncIterator[Series]` (only if the endpoint paginates)

OpenAPI parameters for `GET /series`:
- `category: str | None`
- `tags: str | None` (string per OpenAPI; treat as raw query value)
- `include_product_metadata: bool = False`
- `include_volume: bool = False`

OpenAPI parameters for `GET /series/{series_ticker}`:
- `include_volume: bool = False`

SSOT: `https://docs.kalshi.com/openapi.yaml`

#### 2.2 Structured targets endpoints

Add models in `src/kalshi_research/api/models/`:

- `structured_target.py`: `StructuredTargetSummary`, `StructuredTarget`, response wrappers

Add client methods:

- `get_structured_targets_page(type: str|None, competition: str|None, page_size: int = 100, cursor: str|None)`
- `get_all_structured_targets(...) -> AsyncIterator[StructuredTargetSummary]`
- `get_structured_target(structured_target_id: str) -> StructuredTarget`

OpenAPI parameters for `GET /structured_targets`:
- `type: str | None`
- `competition: str | None`
- `page_size: int (1..2000, default 100)`
- `cursor: str | None`

SSOT: `https://docs.kalshi.com/openapi.yaml`

#### 2.3 Multivariate events

Add:

- `get_multivariate_events_page(series_ticker: str|None, collection_ticker: str|None, with_nested_markets: bool = False, limit: int = 100, cursor: str|None)`
- `get_all_multivariate_events(...) -> AsyncIterator[Event]` (or a dedicated model if schema differs)

OpenAPI notes:
- `collection_ticker` cannot be combined with `series_ticker`.

SSOT: `https://docs.kalshi.com/openapi.yaml`

---

### 3) CLI surface (minimal, explicit)

#### 3.1 Market time series

Add `kalshi market trades` (public trades):

```bash
uv run kalshi market trades KXBTC-26JAN15-T100000 --min-ts 1700000000 --max-ts 1700100000 --limit 1000 --format json
```

Add `kalshi market candlesticks`:

```bash
uv run kalshi market candlesticks KXBTC-26JAN15-T100000 --start 2026-01-01 --end 2026-01-10 --period 60 --format json
```

Implementation detail:
- Convert ISO dates to Unix seconds at the CLI boundary.
- Do not persist by default; persistence is Phase 2.

#### 3.2 Series / structured target discovery

Add `kalshi market series list/get`:

```bash
uv run kalshi market series list --category economics --include-volume
uv run kalshi market series get JOBS --include-volume
```

Add `kalshi market structured-targets list/get`:

```bash
uv run kalshi market structured-targets list --type sports --page-size 200
uv run kalshi market structured-targets get <structured_target_id>
```

#### 3.3 Data sync (optional Phase 2)

Add `kalshi data sync-series`, `kalshi data sync-structured-targets`, `kalshi data sync-multivariate-events` for
persisted discovery, only after DB tables are added.

---

### 4) Database persistence (Phase 2, only if it pays off)

We persist only if it improves workflows:

- Series + structured targets enable offline browsing and better discovery (and can feed SPEC-028 search/topic
  indexing later).
- Candlesticks/trades persistence is optional and should be justified by a concrete analysis need.

#### 4.1 Tables (proposed)

- `series`
  - `ticker` (PK)
  - `title`
  - `category` (nullable)
  - `tags` (nullable, raw string or JSON)
  - `product_metadata_json` (nullable)
  - `total_volume` (nullable; only if requested from API)
  - timestamps

- `structured_targets`
  - `id` (PK)
  - `type` (nullable)
  - `competition` (nullable)
  - `name/title` (field per OpenAPI)
  - `payload_json` (full canonical JSON for forward compatibility)
  - timestamps

- Optional future mapping tables if OpenAPI reveals stable relationships (don’t invent them up front):
  - `structured_target_series`
  - `structured_target_events`

---

## Implementation Plan

### Phase 1: Client + CLI (no DB changes required)

1. Add `GET /markets` filter parity:
   - `tickers`, `min_*_ts` / `max_*_ts`
   - client-side validation for incompatible filter combinations
2. Add `/series` and `/structured_targets` client + models (from OpenAPI schemas).
3. Add multivariate events client methods.
4. Add CLI commands for:
   - series list/get
   - structured-targets list/get
   - market trades
   - market candlesticks
5. Add unit tests with `respx` for:
   - request parameter serialization (tickers/timestamps)
   - pagination cursor handling (where applicable)
   - schema parsing

### Phase 2: Persistence (only if discovery needs it)

1. Add ORM models + repositories for series/structured targets.
2. Add data sync commands.
3. Update `../_vendor-docs/kalshi-api-reference.md` with any missing details learned from OpenAPI.

---

## Acceptance Criteria

- [ ] `KalshiPublicClient.get_markets_*` supports `tickers` + timestamp filters with client-side validation.
- [ ] Series and structured targets can be listed/fetched from CLI without ad-hoc scripts.
- [ ] Multivariate events are accessible and can be optionally synced.
- [ ] All new code is covered by unit tests and doesn’t require live credentials.
