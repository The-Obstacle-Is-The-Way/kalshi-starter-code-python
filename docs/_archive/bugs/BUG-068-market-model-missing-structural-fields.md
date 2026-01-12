# BUG-068: Market Model Missing Structural Fields

**Priority:** P3
**Status:** ✅ Fixed
**Found:** 2026-01-12
**Fixed:** 2026-01-12
**Verified:** 2026-01-12 - Confirmed none of these fields are used in codebase

---

## Summary

The Market model was missing several structural fields documented in the Kalshi OpenAPI schema. While
not immediately critical, these fields are needed for:
- Understanding market mechanics (scalar vs binary)
- Strike configuration for range-based markets
- Price level structure for subpenny pricing
- Multivariate event support

---

## Fix Implemented

- Expanded `Market` in `src/kalshi_research/api/models/market.py` to include structural OpenAPI fields
  (all optional to avoid breaking older fixtures).
- Added typed models/enums:
  - `MarketType`, `StrikeType`
  - `PriceRange`
  - `MveSelectedLeg`
- Added unit coverage to ensure these fields parse correctly.

---

## Current State

**Location:** `src/kalshi_research/api/models/market.py`

**Missing fields by category:**

### Market Typing (Binary vs Scalar)

| Field | Type (OpenAPI) | Description |
|-------|----------------|-------------|
| `market_type` | enum | `binary` or `scalar` |

> **Note:** `market_type` is `required` in the live OpenAPI `Market` schema.

### Market Metadata (Required)

| Field | Type (OpenAPI) | Description |
|-------|----------------|-------------|
| `yes_sub_title` | string | Shortened title for the YES side |
| `no_sub_title` | string | Shortened title for the NO side |

### Market Type & Strike Configuration

| Field | Type (OpenAPI) | Description |
|-------|------|-------------|
| `strike_type` | enum | `greater`, `greater_or_equal`, `less`, etc. |
| `floor_strike` | number\|null | Minimum expiration value for YES outcome |
| `cap_strike` | number\|null | Maximum expiration value for YES outcome |
| `functional_strike` | string | Mapping formula |
| `custom_strike` | object\|null | Per-target mappings |

### Price Level Structure (Subpenny Pricing)

| Field | Type (OpenAPI) | Description |
|-------|------|-------------|
| `price_level_structure` | string | Pricing rules (e.g., `custom`) |
| `price_ranges` | array | Allowed price ranges with start, end, tick size |
| `tick_size` | int (deprecated) | Deprecated; OpenAPI still includes this field |

### Time & Settlement

| Field | Type (OpenAPI) | Description |
|-------|------|-------------|
| `expected_expiration_time` | datetime | Projected settlement time |
| `latest_expiration_time` | datetime | Latest possible expiration time |
| `settlement_timer_seconds` | int | Countdown before settlement |
| `can_close_early` | bool | Whether the market can close early |
| `settlement_value` | int\|null | YES payout in cents (post-determination) |
| `settlement_value_dollars` | string\|null | YES payout in dollars (post-determination) |
| `expiration_value` | string | Value used for settlement |
| `rules_primary` | string | Primary rules text |
| `rules_secondary` | string | Secondary rules text |

### Other

| Field | Type (OpenAPI) | Description |
|-------|------|-------------|
| `is_provisional` | bool | Market may be deleted if no activity |
| `fee_waiver_expiration_time` | datetime | When promotional fee waiver ends |
| `early_close_condition` | string\|null | Condition for early close |
| `primary_participant_key` | string\|null | Primary participant identifier |
| `mve_collection_ticker` | string | Multivariate collection ticker |
| `mve_selected_legs` | array | Selected legs in multivariate combination |

---

## Evidence from Live OpenAPI (2026-01-12)

Kalshi publishes the canonical schema at `https://docs.kalshi.com/openapi.yaml`.
The `Market` schema includes these fields (many as `required`), but our Pydantic Market model does not
currently expose them.

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
4. Model `price_ranges` as a typed list (e.g., `list[PriceRange]`) consistent with OpenAPI

---

## Test Plan

- [x] Add fields to Market model
- [x] Add unit coverage for parsing structural fields
- [ ] Verify parsing from live API with diverse market types (follow-up)

---

## Related

- BUG-063: Missing dollar fields
- DEBT-014: General API field tracking
