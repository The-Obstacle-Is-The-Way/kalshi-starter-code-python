# SPEC-027: Settlement Timestamp Support

**Priority:** Medium
**Status:** Approved
**Created:** 2026-01-09
**Effort:** ~2-3 hours
**Supersedes:** DEBT-004

---

## Summary

Add support for the `settlement_ts` field that Kalshi added to the API on Dec 19, 2025. Currently, we use `expiration_time` as a proxy for settlement time, which is semantically incorrect.

---

## Background

### Current State (Incorrect)

```python
# src/kalshi_research/data/fetcher.py
def _api_market_to_settlement(self, api_market: APIMarket) -> DBSettlement | None:
    return DBSettlement(
        settled_at=api_market.expiration_time,  # PROXY - not actual settlement time
        ...
    )
```

**Problem:** Markets can settle early (event resolved before expiration) or late (disputes, delays).

### API Update (Dec 19, 2025)

Kalshi added `settlement_ts` to `GET /markets` and `GET /markets/{ticker}` responses:

```json
{
  "ticker": "KXBTC-26JAN15-T100000",
  "status": "finalized",
  "result": "yes",
  "settlement_ts": "2026-01-15T18:00:00Z",  // NEW - actual settlement time
  "expiration_time": "2026-01-16T00:00:00Z"
}
```

---

## Implementation Plan

### 1. Update API Model

**File:** `src/kalshi_research/api/models/market.py`

```python
class Market(BaseModel):
    # ... existing fields ...

    # Timestamps
    created_time: datetime | None = Field(default=None, description="When the market was created")
    open_time: datetime
    close_time: datetime
    expiration_time: datetime

    # Settlement (only populated for settled markets)
    settlement_ts: datetime | None = Field(
        default=None,
        description="Actual settlement timestamp. None if not yet settled."
    )
```

### 2. Update Data Fetcher

**File:** `src/kalshi_research/data/fetcher.py`

```python
def _api_market_to_settlement(self, api_market: APIMarket) -> DBSettlement | None:
    if not api_market.result:
        return None

    # Prefer actual settlement_ts, fall back to expiration_time for historical data
    settled_at = api_market.settlement_ts or api_market.expiration_time

    return DBSettlement(
        ticker=api_market.ticker,
        event_ticker=api_market.event_ticker,
        settled_at=settled_at,
        result=api_market.result,
    )
```

### 3. Update Vendor Documentation

**File:** `docs/_vendor-docs/kalshi-api-reference.md`

Add to Market Response Fields section:

```markdown
### Settlement Fields (Dec 19, 2025+)

| Field | Type | Description |
|-------|------|-------------|
| `settlement_ts` | datetime | Actual settlement timestamp (null if not settled) |
| `settlement_value` | int | Settlement value in cents (YES side) |
| `settlement_value_dollars` | string | Settlement value in dollars |
| `settlement_timer_seconds` | int | Duration before settlement after determination |
```

### 4. Update Skills Documentation

**File:** `.claude/skills/kalshi-cli/DATABASE.md`

Update the settlements table documentation:

```markdown
### settlements

| Column | Type | Description |
|--------|------|-------------|
| `ticker` | TEXT PK | Market ticker (FK to markets) |
| `event_ticker` | TEXT | Parent event |
| `settled_at` | DATETIME | **Actual** settlement timestamp (from API `settlement_ts`) |
| `result` | TEXT | Outcome: yes, no, void |

**Note:** For markets settled before Dec 19, 2025, `settled_at` may use `expiration_time` as a proxy.
```

### 5. Add Tests

**File:** `tests/unit/api/test_models.py`

```python
def test_market_with_settlement_ts():
    """Market model parses settlement_ts correctly."""
    data = {
        "ticker": "TEST-123",
        "event_ticker": "TEST",
        "title": "Test Market",
        "status": "finalized",
        "result": "yes",
        "settlement_ts": "2026-01-15T18:00:00Z",
        "expiration_time": "2026-01-16T00:00:00Z",
        # ... other required fields
    }
    market = Market.model_validate(data)
    assert market.settlement_ts is not None
    assert market.settlement_ts < market.expiration_time  # Settled early


def test_market_without_settlement_ts():
    """Market model handles missing settlement_ts (unsettled market)."""
    data = {
        "ticker": "TEST-123",
        # ... no settlement_ts
    }
    market = Market.model_validate(data)
    assert market.settlement_ts is None
```

**File:** `tests/unit/data/test_fetcher.py`

```python
def test_api_market_to_settlement_prefers_settlement_ts():
    """Fetcher uses settlement_ts over expiration_time when available."""
    # ... test implementation
```

---

## Acceptance Criteria

- [ ] `settlement_ts: datetime | None` added to `Market` model
- [ ] `_api_market_to_settlement` prefers `settlement_ts` over `expiration_time`
- [ ] Vendor docs updated with settlement fields documentation
- [ ] Skills docs (all 3 mirrors) updated with correct schema
- [ ] Unit tests for model parsing and fetcher logic
- [ ] All quality gates pass (ruff, mypy, pytest)

---

## Files to Modify

| File | Change |
|------|--------|
| `src/kalshi_research/api/models/market.py` | Add `settlement_ts` field |
| `src/kalshi_research/data/fetcher.py` | Use `settlement_ts` with fallback |
| `docs/_vendor-docs/kalshi-api-reference.md` | Document settlement fields |
| `.claude/skills/kalshi-cli/DATABASE.md` | Update settlements schema |
| `.codex/skills/kalshi-cli/DATABASE.md` | Mirror update |
| `.gemini/skills/kalshi-cli/DATABASE.md` | Mirror update |
| `tests/unit/api/test_models.py` | Add tests |
| `tests/unit/data/test_fetcher.py` | Add tests |

---

## Why This Is a Spec, Not Debt

This was originally tracked as DEBT-004 (technical debt), but it's actually a **feature gap**:

1. The API provides `settlement_ts` (since Dec 25, 2025)
2. Our model doesn't consume it
3. Our docs don't mention it
4. Users cannot access accurate settlement timing

Technical debt implies "code that works but could be better." This is "code that's missing functionality the API provides."

---

## References

- [Kalshi API Changelog - settlement_ts (Dec 19, 2025)](https://docs.kalshi.com/changelog)
- [Get Market API](https://docs.kalshi.com/api-reference/market/get-market)
- DEBT-004 (superseded by this spec)
