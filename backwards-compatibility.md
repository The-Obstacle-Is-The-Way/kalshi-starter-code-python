# Backwards Compatibility Debt

**This is a greenfield project.** Backwards compatibility should be minimal or non-existent until we have actual users depending on specific behaviors.

## Why This Matters

Excessive backwards compatibility in a greenfield project is **anti-pattern**:

| Problem | Impact |
|---------|--------|
| **Complexity without users** | No one depends on the old behavior, so we're solving a problem that doesn't exist |
| **Cognitive load** | AI agents and humans can't tell which code path is "real" vs "legacy" |
| **Testing burden** | Tests cover paths that will never execute in production |
| **Drift risk** | Fallback paths bit-rot since they're never exercised |
| **False confidence** | Having fallbacks suggests code handles cases it may never see |

**The greenfield principle:** Start clean, add compatibility only when you have actual users who need migration time.

---

## Inventory of Backwards Compatibility in Codebase

### Category 1: Kalshi API Field Deprecations (External Dependency)

These exist because Kalshi deprecated fields but hasn't removed them yet. **Some of this is justified** (we need to work with the current API), but we can simplify after Jan 15, 2026.

#### 1.1 Market Model - Cents vs Dollars Fields

**Location:** `src/kalshi_research/api/models/market.py:71-76, 135-171`

**What's there:**
```python
# Legacy pricing (DEPRECATED: removed Jan 15, 2026 - use *_dollars fields)
yes_bid: int | None = Field(default=None, ge=0, le=100, description="DEPRECATED")
yes_ask: int | None = Field(default=None, ge=0, le=100, description="DEPRECATED")
no_bid: int | None = Field(default=None, ge=0, le=100, description="DEPRECATED")
no_ask: int | None = Field(default=None, ge=0, le=100, description="DEPRECATED")
last_price: int | None = Field(default=None, ge=0, le=100, description="DEPRECATED")

# ...plus 5 computed properties that "prefer dollars, fallback to legacy"
```

**Why it's problematic:**
- 5 deprecated fields + 5 computed properties with fallback logic
- The fallbacks add complexity for fields that may never be populated
- After Jan 15, the cents fields will never have values

**Recommendation:** After Jan 15, 2026:
- Remove the deprecated `yes_bid`, `yes_ask`, `no_bid`, `no_ask`, `last_price` fields entirely
- Simplify computed properties to just convert from dollars (no fallback)

---

#### 1.2 Market Model - Liquidity Field Handler

**Location:** `src/kalshi_research/api/models/market.py:93-133`

**What's there:**
```python
liquidity: int | None = Field(
    default=None,
    description="DEPRECATED: Use dollar-denominated fields. Removed Jan 15, 2026.",
)

@field_validator("liquidity", mode="before")
def handle_deprecated_liquidity(cls, v: int | None) -> int | None:
    """Handle deprecated liquidity field gracefully."""
    if v is None:
        return None
    if v < 0:
        logger.warning("Received negative liquidity value...")
        return None
    return v
```

**Why it's problematic:**
- Validator handles edge case (negative liquidity) for a field being removed
- After Jan 15, this field won't exist in responses

**Recommendation:** After Jan 15, 2026:
- Remove the field and validator entirely

---

#### 1.3 Orderbook Model - Dual Format Support

**Location:** `src/kalshi_research/api/models/orderbook.py`

**What's there:**
```python
# Each level is [price_cents, quantity] - DEPRECATED Jan 15, 2026
yes: list[tuple[int, int]] | None = None
no: list[tuple[int, int]] | None = None

# Dollar-denominated versions
yes_dollars: list[tuple[str, int]] | None = None
no_dollars: list[tuple[str, int]] | None = None
```

Plus 4 computed properties with fallback logic:
- `yes_levels` - prefers dollars, falls back to cents
- `no_levels` - prefers dollars, falls back to cents
- `best_yes_bid` - uses above
- `best_no_bid` - uses above

**Why it's problematic:**
- 4 fields for the same 2 pieces of data (YES levels, NO levels)
- Complex fallback logic in computed properties
- Confusing for anyone reading the code

**Recommendation:** After Jan 15, 2026:
- Remove `yes` and `no` fields entirely
- Simplify properties to just use `*_dollars` fields

---

#### 1.4 Candlestick Models - Dual Format Fields

**Location:** `src/kalshi_research/api/models/candlestick.py`

**What's there:**
```python
# Integer cents (deprecated)
open: int | None = None
high: int | None = None
low: int | None = None
close: int | None = None

# Dollar strings (new)
open_dollars: str | None = None
high_dollars: str | None = None
low_dollars: str | None = None
close_dollars: str | None = None
```

**Why it's problematic:**
- 8 fields for 4 pieces of data (OHLC)
- No computed properties to normalize - users must check both

**Recommendation:** After Jan 15, 2026:
- Remove cent fields, keep only `*_dollars`
- Or add computed properties like Market model has

---

### Category 2: Internal Format Migration (No External Users)

These backwards compatibility layers exist for **internal data format changes** where there are no external users to support.

#### 2.1 Thesis Storage - Legacy Dict Format

**Location:** `src/kalshi_research/research/thesis.py:324-342`

**What's there:**
```python
# Legacy dict format: {"<id>": {...}, ...}
loaded_from_mapping: dict[str, Thesis] = {}
for key, value in raw.items():
    if not isinstance(value, dict):
        continue
    thesis_dict = dict(value)
    thesis_dict.setdefault("id", key)
    # ... parse legacy format
```

**Why it's problematic:**
- Supports a format that may have never been used in production
- Adds ~20 lines of parsing code for a hypothetical migration
- New format (`{"theses": [...]}`) is already the save format

**Recommendation:**
- Check if any users have the old format (likely none)
- If none, delete the legacy parsing code entirely
- If some exist, provide a one-time migration script instead of runtime compat

---

#### 2.2 Portfolio Positions Response Key Fallback

**Location:** `src/kalshi_research/api/client.py:581-582`

**What's there:**
```python
# NOTE: Kalshi returns `market_positions` (and `event_positions`). Older docs/examples may
# reference `positions`, so keep a fallback for compatibility.
raw = data.get("market_positions") or data.get("positions") or []
```

**Why it's problematic:**
- Fallback to `positions` is based on "older docs" that may be outdated
- If Kalshi consistently returns `market_positions`, the fallback never triggers
- Adds uncertainty about what the "real" key is

**Recommendation:**
- Verify Kalshi's current response (check API or OpenAPI spec)
- If always `market_positions`, remove fallback
- If varies, document when each is used

---

#### 2.3 Data Fetcher - Settlement Time Fallback

**Location:** `src/kalshi_research/data/fetcher.py:132-133`

**What's there:**
```python
Prefer `settlement_ts` (added Dec 19, 2025) when available. Fall back to
`Market.expiration_time` for historical/legacy data.
```

**Why it's problematic:**
- Fallback for "historical data" that may not exist
- Creates two code paths for the same concept

**Recommendation:**
- If no historical data exists yet, just use `settlement_ts`
- If historical data exists, migrate it once instead of runtime fallback

---

### Category 3: Database Schema Decisions

#### 3.1 Database Stores Cents, API Returns Dollars

**Location:** `src/kalshi_research/data/fetcher.py:112-113`

**What's there:**
```python
Uses computed properties that prefer new dollar fields over legacy cent fields.
Database continues to store cents for backwards compatibility.
```

**Why it's problematic:**
- Conversion happens in multiple places
- Confusion about what format data is in
- After Jan 15, API only returns dollars, but DB stores cents

**Recommendation:**
- **Keep as-is for now** - cents are actually better for calculations (no floating point)
- But document clearly that this is intentional, not backwards compat
- Consider renaming the comment to "Database stores cents for precision" (not "backwards compatibility")

---

### Category 4: Exa API Compatibility

#### 4.1 Livecrawl Fallback Mode

**Location:** `src/kalshi_research/exa/client.py:332`, `src/kalshi_research/exa/models/common.py:15`

**What's there:**
```python
class LivecrawlMode(str, Enum):
    FALLBACK = "fallback"
    PREFERRED = "preferred"
    NEVER = "never"

# Used as default:
livecrawl: str = "fallback",
```

**Status:** This is **NOT backwards compatibility** - it's a legitimate Exa API feature. The term "fallback" refers to Exa's crawling strategy, not code compatibility.

**Recommendation:** No change needed - this is correct API usage.

---

## Summary Table

| Issue | Type | Priority | Action |
|-------|------|----------|--------|
| Market cents fields | External API | P1 | Remove after Jan 15, 2026 |
| Market liquidity validator | External API | P2 | Remove after Jan 15, 2026 |
| Orderbook dual format | External API | P1 | Remove cents after Jan 15, 2026 |
| Candlestick dual format | External API | P2 | Remove cents after Jan 15, 2026 |
| Thesis legacy dict format | Internal | **P0** | Remove now (no users) |
| Portfolio positions fallback | Internal | P2 | Verify and remove |
| Settlement time fallback | Internal | P2 | Verify and remove |
| DB cents storage | Internal | P3 | Keep (rename comment) |

---

## Cleanup Checklist

### Immediate (No Users Depend On These)

- [ ] Remove thesis legacy dict format parsing
- [ ] Verify portfolio `positions` vs `market_positions` - remove if unused
- [ ] Verify settlement_ts availability - remove fallback if always present

### After Jan 15, 2026 (Kalshi Deprecation Date)

- [ ] Remove Market model deprecated fields: `yes_bid`, `yes_ask`, `no_bid`, `no_ask`, `last_price`, `liquidity`
- [ ] Simplify Market computed properties (remove fallback logic)
- [ ] Remove Orderbook `yes` and `no` fields
- [ ] Simplify Orderbook computed properties
- [ ] Remove Candlestick cent fields if not needed

### Documentation

- [ ] Update comments that say "backwards compatibility" to be specific about what they're compatible with
- [ ] Remove TODO/DEPRECATED comments for things that are no longer deprecated (after cleanup)

---

## Anti-Pattern Detection Guide

When reviewing code, flag these patterns in a greenfield project:

1. **"or []" / "or {}" fallbacks** - Ask: "What case produces the empty fallback?"
2. **".get(key) or .get(other_key)"** - Ask: "When is `other_key` used? Is this documented?"
3. **"Legacy format" comments** - Ask: "Do any users have this format? Can we migrate instead?"
4. **Dual field storage** (e.g., cents AND dollars) - Ask: "Can we pick one and convert?"
5. **"Prefer X, fallback to Y"** - Ask: "When does Y trigger? Is it tested?"

---

## References

- [Kalshi API Changelog](https://docs.kalshi.com/changelog) - Field deprecation dates
- `hacks.md` - Related workarounds and missing API features
- `docs/_vendor-docs/kalshi-api-reference.md` - Current API documentation
