# TODO-009: Cent-Denominated Field Deprecation Migration

**Priority**: 🚨 CRITICAL
**Status**: Active
**Created**: 2026-01-09
**Deadline**: 2026-01-15 (6 DAYS)

## Context

Per [Kalshi API Changelog](https://docs.kalshi.com/changelog), the following cent-denominated fields are being **REMOVED** from Market responses on **January 15, 2026**:

### Fields Being Removed

| Field | Replacement | Notes |
|-------|-------------|-------|
| `yes_bid` | `yes_bid_dollars` | String like "0.4500" |
| `yes_ask` | `yes_ask_dollars` | String like "0.4700" |
| `no_bid` | `no_bid_dollars` | String like "0.5300" |
| `no_ask` | `no_ask_dollars` | String like "0.5500" |
| `last_price` | `last_price_dollars` | String |
| `previous_price` | `previous_price_dollars` | String |
| `previous_yes_bid` | `previous_yes_bid_dollars` | String |
| `previous_yes_ask` | `previous_yes_ask_dollars` | String |
| `liquidity` | **NONE** | ✅ Already handled (BUG-048) |
| `notional_value` | **NONE** | Calculate from price * contracts |
| `tick_size` | `price_level_structure`, `price_ranges` | New structure |
| `response_price_units` | **NONE** | Always dollars now |

## Impact Assessment

### High Impact (Core Model)
- **`Market` model** (`api/models/market.py`) - Uses `yes_bid`, `yes_ask`, `no_bid`, `no_ask` as `int` fields
- **`PriceSnapshot` model** (`data/models.py`) - Stores int prices in database

### Medium Impact (Analysis)
- **`MarketScanner`** (`analysis/scanner.py`) - Calculates midpoint, spread from int prices
- **`EdgeDetector`** (`analysis/edge.py`) - Uses prices for edge calculations

### Low Impact (Display)
- **CLI commands** - Display prices (can format dollars)

## Migration Strategy

### Option A: Dual Support (Recommended for Smooth Transition)

1. Add new `*_dollars` fields to Market model as optional
2. Add computed properties that prefer dollars, fallback to cents
3. Deprecate cent fields over time
4. Remove cent fields after Jan 15

```python
# Example migration pattern
class Market(BaseModel):
    # New fields (strings from API)
    yes_bid_dollars: str | None = None
    yes_ask_dollars: str | None = None

    # Legacy fields (deprecated, may be removed by API)
    yes_bid: int | None = None
    yes_ask: int | None = None

    @property
    def yes_bid_cents(self) -> int:
        """Get yes_bid in cents, preferring dollars field."""
        if self.yes_bid_dollars:
            return int(Decimal(self.yes_bid_dollars) * 100)
        return self.yes_bid or 0
```

### Option B: Hard Cut (Simpler but Riskier)

1. Replace all int price fields with string dollar fields on Jan 15
2. Update all code to parse strings
3. Risk: Breaking change if API timing differs

## Definition of Done

- [x] Add `*_dollars` fields to `Market` model (yes_bid_dollars, yes_ask_dollars, no_bid_dollars, no_ask_dollars, last_price_dollars, previous_*_dollars)
- [x] Add validators to parse dollar strings to Decimal (field validators implemented)
- [x] Add computed properties for backwards compatibility (yes_bid_cents, yes_ask_cents, no_bid_cents, no_ask_cents, last_price_cents)
- [x] Add midpoint and spread properties to Market model for cleaner analysis code
- [x] Update `MarketScanner` to use computed properties (scanner.py updated)
- [x] Update `EdgeDetector` to use computed properties (implicitly via scanner)
- [x] Update CLI display formatting (market.py, scan.py updated)
- [x] Update data fetcher to convert dollars → cents for PriceSnapshot storage (fetcher.py updated)
- [x] Update all other code using price fields (alerts, correlation, metrics, portfolio, research updated)
- [x] Update tests for new model structure (471 tests pass)
- [ ] Verify against live API after Jan 15 (pending - deadline not yet reached)

## Risk Mitigation

1. **Test against demo API first** - Demo may update before prod
2. **Add defensive parsing** - Handle both formats during transition
3. **Monitor for 500 errors** - API may return errors if old fields requested

## Related Files

- `src/kalshi_research/api/models/market.py`
- `src/kalshi_research/data/models.py`
- `src/kalshi_research/data/fetcher.py`
- `src/kalshi_research/analysis/scanner.py`
- `src/kalshi_research/analysis/edge.py`
- `docs/_vendor-docs/kalshi-api-reference.md`

## Sources

- [Kalshi API Changelog](https://docs.kalshi.com/changelog) - Breaking changes
- [Kalshi OpenAPI Spec](https://docs.kalshi.com/openapi.yaml) - Field definitions
