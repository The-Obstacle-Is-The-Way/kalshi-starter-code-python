# FUTURE-002: Kalshi Blocked/Unimplemented Endpoints

**Status:** Tracking
**Created:** 2026-01-16
**Revisit:** Q2 2026 (Subaccounts), Periodically (others)

---

## Summary

This document tracks Kalshi API endpoints that are **not implemented** in our client, along with the reasons and
conditions under which we would implement them.

**Current coverage:** 50/74 endpoints (68%)

---

## Endpoints to Revisit (May Become Available)

### 1. Subaccounts (4 endpoints) - Revisit Q2 2026

**Added to Kalshi API:** Jan 9, 2026 (per [changelog](https://docs.kalshi.com/changelog))

| Endpoint | Observed (2026-01-15) |
|----------|------------------|
| `POST /portfolio/subaccounts` | 404 in demo + prod |
| `GET /portfolio/subaccounts/balances` | 403 in prod ("not available in production") |
| `POST /portfolio/subaccounts/transfer` | 404 in demo + prod |
| `GET /portfolio/subaccounts/transfers` | 403 in prod ("not available in production") |

**Why blocked:** Feature is brand new (7 days old when we tested). Likely in phased rollout / account-permission gated.

**Value if available:**
- Track "Macro Thesis" vs "Crypto Thesis" separately
- Know which strategies are actually profitable
- Proper capital allocation across approaches

**Action items:**
- [ ] Re-check in Q2 2026
- [ ] Contact Kalshi support to request access
- [ ] Implement when API returns real responses

### 2. Forecast Percentile History (1 endpoint) - Check Periodically

**Added to Kalshi API:** Sep 11, 2025

| Endpoint | Observed (2026-01-15) |
|----------|------------------|
| `GET /series/{series_ticker}/events/{ticker}/forecast_percentile_history` | Unverified 200 payload (see notes) |

**SSOT (OpenAPI):** This endpoint requires auth and requires query params: `percentiles`, `start_ts`, `end_ts`,
`period_interval`. Without valid parameters, Kalshi will return `400 bad_request`.

**Changelog vs OpenAPI:** The Sep 11, 2025 changelog entry calls this `GET /forecast_percentiles_history` (no series/event
path). The current OpenAPI defines the series/event-scoped path above.

**Why blocked/unimplemented:** We have not recorded a stable `200` response fixture yet. Until we can, treat this as
unimplemented.

**Value if available:**
- Historical forecast accuracy for calibration research
- Know when to fade vs follow the crowd
- Calibration edge at extremes

**Action items:**
- [ ] Re-check periodically
- [ ] Try different event types when available

---

## Intentionally Not Implemented (Institutional/Security)

These endpoints exist in the OpenAPI but are intentionally not implemented for our use case.

### 3. RFQ/Communications (11 endpoints) - Institutional Only

| Endpoint | Reason |
|----------|--------|
| `GET /communications/id` | Large block trades (1000+ contracts) |
| `POST /communications/rfqs` | Institutional use |
| `GET /communications/rfqs` | Institutional use |
| `GET /communications/rfqs/{rfq_id}` | Institutional use |
| `DELETE /communications/rfqs/{rfq_id}` | Institutional use |
| `POST /communications/quotes` | Institutional use |
| `GET /communications/quotes` | Institutional use |
| `GET /communications/quotes/{quote_id}` | Institutional use |
| `DELETE /communications/quotes/{quote_id}` | Institutional use |
| `PUT /communications/quotes/{quote_id}/accept` | Institutional use |
| `PUT /communications/quotes/{quote_id}/confirm` | Institutional use |

**Would implement if:** Trading very large positions where orderbook liquidity is insufficient.

### 4. FCM (2 endpoints) - Explicitly Institutional

| Endpoint | Reason |
|----------|--------|
| `GET /fcm/orders` | FCM members only |
| `GET /fcm/positions` | FCM members only |

Per changelog: "This endpoint requires FCM member access level... only intended for use by FCM members (rare)"

**Would implement if:** Building a brokerage integration.

### 5. API Keys (4 endpoints) - Security Risk

| Endpoint | Reason |
|----------|--------|
| `GET /api_keys` | Security risk |
| `POST /api_keys` | Security risk |
| `POST /api_keys/generate` | Security risk |
| `DELETE /api_keys/{api_key}` | Security risk |

**Why not:** Programmatic API key management is a security risk. Better managed via Kalshi web UI with 2FA.

**Would implement if:** Building a multi-user service that needs to manage keys programmatically.

### 6. Multivariate Low-Value (2 endpoints) - Low Priority

| Endpoint | Reason |
|----------|--------|
| `POST /multivariate_event_collections/{collection_ticker}` | Create market in collection (advanced/rarely needed) |
| `GET /multivariate_event_collections/{collection_ticker}/lookup` | Lookup history (requires `lookback_seconds`, niche use) |

**Would implement if:** Need to create combo markets or analyze historical lookups.

---

## Key Insight: Tiers ≠ Feature Access

Kalshi's **Basic/Advanced/Premier/Prime** tiers control **rate limits** (request throughput):

| Tier | Read/sec | Write/sec |
|------|----------|-----------|
| Basic | 20 | 10 |
| Advanced | 30 | 30 |
| Premier | 100 | 100 |
| Prime | 400 | 400 |

Rate limits are not a guarantee of endpoint access. Some endpoints/features are permissioned by API usage level
(e.g., OpenAPI restricts creating API keys with user-provided RSA keys to Premier/Market Maker usage levels).

---

## Cross-References

| Item | Relationship |
|------|--------------|
| DEBT-015 | Detailed endpoint analysis |
| `kalshi-openapi-coverage.md` | Coverage tracking |
| `kalshi-api-reference.md` | Vendor docs with access categories |
