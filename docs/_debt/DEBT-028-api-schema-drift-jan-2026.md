# DEBT-028: API Schema Drift - January 2026 Migration

**Priority:** P2 (Forward compatibility - deprecation imminent/live)
**Status:** Open
**Created:** 2026-01-15
**Related:** DEBT-025, vendor-docs/kalshi-api-reference.md

---

## Summary

Kalshi's January 15, 2026 API migration removes deprecated cent fields from Market responses. Our codebase has these fields marked as optional/deprecated but they may still be referenced in some code paths. Additionally, live API testing discovered 3 fields that can be `null` despite not being documented as optional.

---

## 1. Cent Field Deprecation (Jan 15, 2026 - TODAY)

### Fields Being Removed from `/markets` Response

Per `docs/_vendor-docs/kalshi-api-reference.md`, these fields are removed as of today:

| Removed Field | Replacement | Status in Our Models |
|---------------|-------------|---------------------|
| `yes_bid` | `yes_bid_dollars` | ✅ Optional, marked DEPRECATED |
| `yes_ask` | `yes_ask_dollars` | ✅ Optional, marked DEPRECATED |
| `no_bid` | `no_bid_dollars` | ✅ Optional, marked DEPRECATED |
| `no_ask` | `no_ask_dollars` | ✅ Optional, marked DEPRECATED |
| `last_price` | `last_price_dollars` | ✅ Optional, marked DEPRECATED |
| `previous_price` | `previous_price_dollars` | ✅ Optional, marked DEPRECATED |
| `previous_yes_bid` | `previous_yes_bid_dollars` | ✅ Optional, marked DEPRECATED |
| `previous_yes_ask` | `previous_yes_ask_dollars` | ✅ Optional, marked DEPRECATED |
| `liquidity` | `liquidity_dollars` | ✅ Optional, marked DEPRECATED |
| `notional_value` | `notional_value_dollars` | ✅ Optional, marked DEPRECATED |
| `tick_size` | `price_level_structure`, `price_ranges` | ✅ Optional, marked DEPRECATED |
| `response_price_units` | N/A (removed) | ✅ Optional |
| `risk_limit_cents` | N/A (removed Jan 8) | ✅ Optional |
| `category` | N/A (removed Jan 8) | ✅ Optional |

### Current Model Status

Our `Market` model (`src/kalshi_research/api/models/market.py`) correctly:
- Has all deprecated fields as `Optional` (won't crash if removed)
- Has all `*_dollars` replacement fields
- Has `*_cents` computed properties that convert from dollars

### Action Required: Audit Code Paths

While our models are prepared, we should audit code that might still reference the deprecated cent fields directly:

```bash
# Find direct usages of deprecated fields (not *_cents properties)
rg "\.yes_bid[^_]|\.yes_ask[^_]|\.no_bid[^_]|\.no_ask[^_]|\.last_price[^_]|\.liquidity[^_]" src/
```

**Recommendation:** Run this audit and migrate any remaining direct usages to `*_cents` or `*_dollars` properties.

---

## 2. Nullable Fields Not Documented (Discovered Jan 15, 2026)

Live API testing discovered these fields can be `null` despite not being documented as optional:

### Fixed in commit 8f9bab2

| Model | Field | Discovery |
|-------|-------|-----------|
| `EventMetadataResponse` | `market_details` | API returns `null` for MVE events |
| `EventMetadataResponse` | `settlement_sources` | API returns `null` for some events |
| `GetOrderQueuePositionsResponse` | `queue_positions` | API returns `null` when no positions |

These have been fixed by making the fields optional with default `None`.

### Potential Additional Drift

Other endpoints may have similar undocumented nullability. Consider auditing during fixture refresh:

- `GET /live_data/batch` - Returns 404 for some milestone IDs (expected API behavior, not our bug)
- `GET /portfolio/summary/total_resting_order_value` - Returns 403 on demo (permission limitation)

---

## 3. Cross-Reference: DEBT-025 Subpenny Strategy

DEBT-025 tracks the broader subpenny precision question. The cent field removal accelerates this:

- **Now:** Cent fields removed, only `*_dollars` remains
- **Our policy:** Round-to-nearest-cent (Option A in DEBT-025)
- **Impact:** Our `*_cents` computed properties now solely depend on dollar→cent conversion

---

## Verification Steps

### Immediate (Today)

```bash
# 1. Run live API test to verify no new failures after cent removal
uv run python -c "
import asyncio
from kalshi_research.api.client import KalshiPublicClient

async def test():
    async with KalshiPublicClient() as client:
        markets = await client.get_markets(limit=5)
        for m in markets:
            print(f'{m.ticker}: yes_bid_cents={m.yes_bid_cents}, yes_ask_dollars={m.yes_ask_dollars}')
asyncio.run(test())
"

# 2. Verify deprecated field references
rg "\.yes_bid[^_]|\.yes_ask[^_]|\.no_bid[^_]|\.no_ask[^_]" src/

# 3. Run full test suite
uv run pytest tests/unit/api/ -v
```

### Ongoing

- Weekly fixture refresh (DEBT-016) will catch future schema drift
- Add integration test marker for live API validation

---

## Next Actions

1. **P1:** Run deprecated field audit (command above) and fix any direct usages
2. **P2:** Update golden fixtures to reflect removed fields (next fixture refresh)
3. **P3:** Consider adding live API smoke test to CI (blocked on test credentials in CI)

---

## Cross-References

| Item | Relationship |
|------|--------------|
| DEBT-025 | Subpenny pricing strategy (rounding policy) |
| DEBT-016 | Fixture drift detection CI |
| `docs/_vendor-docs/kalshi-api-reference.md` | SSOT for breaking changes |
| Commit 8f9bab2 | Nullable field fixes |
