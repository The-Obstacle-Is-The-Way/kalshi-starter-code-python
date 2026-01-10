# DEBT-004: Settlement Timestamp Proxy

**Priority:** Low-Medium
**Status:** RESOLVED (Implemented via [SPEC-027](../_archive/specs/SPEC-027-settlement-timestamp.md))
**Created:** 2026-01-09
**Effort:** ~2-3 hours

> **Note:** This debt item was elevated to a spec because it's a feature gap (API provides
> `settlement_ts`). It has now been implemented; see the archived spec for details.

---

## Problem Statement

The `Settlement` model uses `Market.expiration_time` as a proxy for `Settlement.settled_at`:

```python
# src/kalshi_research/data/fetcher.py:128-143
def _api_market_to_settlement(self, api_market: APIMarket) -> DBSettlement | None:
    """Convert a settled API market to a settlement row.

    Notes:
        Kalshi's public markets endpoint exposes `result` but does not provide a clear
        `settled_at` timestamp. We use `expiration_time` as an explicit proxy for `settled_at`.
    """
    if not api_market.result:
        return None

    return DBSettlement(
        ticker=api_market.ticker,
        event_ticker=api_market.event_ticker,
        settled_at=api_market.expiration_time,  # <-- PROXY
        result=api_market.result,
    )
```

**This is semantically incorrect because:**

1. Markets can settle **EARLY** (event outcome known before expiration)
2. Markets can settle **LATE** (delayed resolution, disputes)
3. Settlement timing analysis is inaccurate

---

## Root Cause

When this code was written, the Kalshi API did not expose a `settlement_ts` field in the public markets endpoint.

**Update (Dec 19, 2025):** Kalshi added a `settlement_ts` field to `GET /markets` and `GET /markets/{ticker}` responses.

Source: [Kalshi API Changelog](https://docs.kalshi.com/changelog)

---

## Current Impact

| Use Case | Impact |
|----------|--------|
| Backtest timing | Low - trades use snapshot timestamps, not settlement |
| Settlement statistics | Medium - "settled at" times are approximate |
| Settlement lag analysis | High - cannot measure actual determination-to-settlement duration |

---

## Solution

### Option A: Use New `settlement_ts` Field (Recommended)

Add `settlement_ts` to the `Market` Pydantic model and use it for `Settlement.settled_at`:

```python
# src/kalshi_research/api/models/market.py
class Market(BaseModel):
    # ... existing fields ...

    # Settlement timestamp (only populated for settled markets)
    settlement_ts: datetime | None = Field(
        default=None,
        description="Actual settlement timestamp (None if not settled)"
    )

# src/kalshi_research/data/fetcher.py
def _api_market_to_settlement(self, api_market: APIMarket) -> DBSettlement | None:
    if not api_market.result:
        return None

    return DBSettlement(
        ticker=api_market.ticker,
        event_ticker=api_market.event_ticker,
        settled_at=api_market.settlement_ts or api_market.expiration_time,  # Prefer real, fallback to proxy
        result=api_market.result,
    )
```

### Option B: Fetch from Portfolio Settlements Endpoint

The `GET /portfolio/settlements` endpoint returns `settled_time` for each position. This requires authentication but provides accurate data.

**Downside:** Only returns markets where the user had positions.

---

## Acceptance Criteria

- [x] Add `settlement_ts: datetime | None` to `Market` model
- [x] Update `_api_market_to_settlement` to prefer `settlement_ts` over `expiration_time`
- [ ] Add migration to update existing settlements with real timestamps (optional)
- [x] Update tests to cover the new field
- [x] Document the fallback behavior in code comments

---

## Files to Modify

| File | Change |
|------|--------|
| `src/kalshi_research/api/models/market.py` | Add `settlement_ts` field |
| `src/kalshi_research/data/fetcher.py` | Use `settlement_ts` with fallback |
| `tests/unit/api/test_models.py` | Add tests for `settlement_ts` |
| `docs/_vendor-docs/kalshi-api-reference.md` | Document the field |

---

## Deferral Justification

This is **Low-Medium priority** because:

1. The proxy is documented (docstring explains the limitation)
2. Most research use cases don't need precise settlement timing
3. The fallback to `expiration_time` is reasonable for ~90% of markets

**Implement when:**
- Building settlement lag analysis features
- Accuracy of "time to resolution" metrics matters
- After other higher-priority work is complete

---

## References

- [Kalshi API Changelog - settlement_ts](https://docs.kalshi.com/changelog)
- [Get Market API](https://docs.kalshi.com/api-reference/market/get-market)
- [Get Settlements API](https://docs.kalshi.com/api-reference/portfolio/get-settlements)
