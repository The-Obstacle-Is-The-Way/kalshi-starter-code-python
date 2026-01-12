# BUG-068: Market Model Missing Structural Fields

**Priority:** P3
**Status:** Open
**Found:** 2026-01-12

---

## Summary

The Market model is missing several structural fields documented in the Kalshi API. While not immediately critical, these fields are needed for:
- Understanding market mechanics (scalar vs binary)
- Strike configuration for range-based markets
- Price level structure for subpenny pricing
- Multivariate event support

---

## Current State

**Location:** `src/kalshi_research/api/models/market.py`

**Missing fields by category:**

### Market Type & Strike Configuration

| Field | Type | Description |
|-------|------|-------------|
| `market_type` | enum | `binary` or `scalar` |
| `strike_type` | enum | `greater`, `greater_or_equal`, `less`, etc. |
| `floor_strike` | int | Minimum expiration value for YES outcome |
| `cap_strike` | int | Maximum expiration value for YES outcome |
| `functional_strike` | string | Mapping formula |
| `custom_strike` | object | Per-target mappings |

### Price Level Structure (Subpenny Pricing)

| Field | Type | Description |
|-------|------|-------------|
| `price_level_structure` | string | Pricing rules (e.g., `custom`) |
| `price_ranges` | array | Allowed price ranges with start, end, step |

### Time & Settlement

| Field | Type | Description |
|-------|------|-------------|
| `expected_expiration_time` | datetime | Projected settlement time |
| `settlement_timer_seconds` | int | Countdown before settlement |

### Other

| Field | Type | Description |
|-------|------|-------------|
| `is_provisional` | bool | Market may be deleted if no activity |
| `fee_waiver_expiration_time` | datetime | When promotional fee waiver ends |
| `early_close_condition` | string | Condition for early close |
| `primary_participant_key` | string | Primary participant identifier |
| `mve_selected_legs` | array | Selected legs in multivariate combination |

---

## Evidence from Vendor Docs

From `docs/_vendor-docs/kalshi-api-reference.md` lines 229-330.

---

## Impact

- Can't properly handle scalar markets (different settlement mechanics)
- Can't validate subpenny pricing compliance
- Can't detect provisional markets that may disappear
- Limited multivariate event support

---

## Fix Required

1. Add missing fields to Market model with appropriate types
2. Consider adding `market_type` enum
3. Add `strike_type` enum
4. Model `price_ranges` as list of dicts or Pydantic model

---

## Test Plan

- [ ] Add fields incrementally
- [ ] Update test fixtures
- [ ] Verify parsing from live API with diverse market types

---

## Related

- BUG-063: Missing dollar fields (higher priority)
- DEBT-014: General API field tracking
