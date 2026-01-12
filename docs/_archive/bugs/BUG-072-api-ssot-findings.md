# BUG-072: API SSOT Findings - Raw Responses vs Models vs Docs

**Priority:** P2 (SSOT alignment + preventing schema hallucinations)
**Status:** ✅ Fixed
**Found:** 2026-01-12
**Fixed:** 2026-01-12
**Method:** Re-recorded **RAW** production API responses → sanitized → validated models vs fixtures

---

## Problem

We previously treated “golden fixtures” as SSOT, but they were **not raw API responses**. They were produced after
our client parsed and reshaped the data, which caused:

- Incorrect conclusions in bug docs (wrapper keys missing, wrong response keys)
- Validation scripts pointing at fake paths (e.g., `response.positions` instead of `response.market_positions`)

---

## Fix Implemented

1. Deleted stale fixtures in `tests/fixtures/golden/`
2. Re-recorded fixtures from production using raw HTTP response JSON:
   - Public endpoints: `KalshiPublicClient._get(...)`
   - Auth endpoints: `KalshiClient._auth_get(...)`
3. Sanitized authenticated fixtures with `scripts/sanitize_golden_fixtures.py`
4. Updated `scripts/validate_models_against_golden.py` to match real wrapper keys and page keys
5. Updated models to match observed production fields:
   - `PortfolioBalance.updated_ts`
   - `PortfolioPosition` extended fields (including `*_dollars` and `last_updated_ts`)
   - `Fill.ts`

---

## Golden Fixture Format (SSOT)

Each file in `tests/fixtures/golden/` is stored as:

```json
{
  "_metadata": { "...": "..." },
  "response": { "...": "RAW API JSON ..." }
}
```

The SSOT is the `response` object (not our client-parsed models).

---

## SSOT Answers (Production, 2026-01-12)

### Public endpoints

- `GET /markets` → `response = {"cursor": ..., "markets": [...]}` (`tests/fixtures/golden/markets_list_response.json`)
- `GET /markets/{ticker}` → `response = {"market": {...}}` (`tests/fixtures/golden/market_single_response.json`)
- `GET /markets/{ticker}/orderbook` → `response = {"orderbook": {...}}` (`tests/fixtures/golden/orderbook_response.json`)
- `GET /events` → `response = {"cursor": ..., "events": [...], "milestones": [...]}` (`tests/fixtures/golden/events_list_response.json`)
- `GET /events/{event_ticker}` → `response = {"event": {...}, "markets": [...]}` (`tests/fixtures/golden/event_single_response.json`)
- `GET /exchange/status` → `response = {"exchange_active": ..., "trading_active": ..., "exchange_estimated_resume_time": ...}` (`tests/fixtures/golden/exchange_status_response.json`)

### Portfolio endpoints (authenticated)

- `GET /portfolio/balance` → `response = {"balance": <int>, "portfolio_value": <int>, "updated_ts": <int>}` (`tests/fixtures/golden/portfolio_balance_response.json`)
- `GET /portfolio/positions` → `response = {"cursor": ..., "market_positions": [...], "event_positions": [...]}` (`tests/fixtures/golden/portfolio_positions_response.json`)
- `GET /portfolio/orders` → `response = {"cursor": ..., "orders": [...]}` (`tests/fixtures/golden/portfolio_orders_response.json`)
- `GET /portfolio/fills` → `response = {"cursor": ..., "fills": [...]}` (`tests/fixtures/golden/portfolio_fills_response.json`)
- `GET /portfolio/settlements` → `response = {"cursor": ..., "settlements": [...]}` (`tests/fixtures/golden/portfolio_settlements_response.json`)

---

## Validation Result

After the fixes above:

```bash
uv run python scripts/validate_models_against_golden.py
```

Reports:

- `RESULT: ALL MODELS MATCH GOLDEN FIXTURES`

---

## Related

- **BUG-071**: Mocked Tests Hide API Reality (root cause)
- **BUG-073**: Vendor docs drift (updated based on raw fixtures)
