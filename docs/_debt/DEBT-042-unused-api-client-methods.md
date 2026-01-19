# DEBT-042: ~30 Unused API Client Methods

**Status:** Active
**Priority:** P4 (Low - API completeness vs. YAGNI)
**Created:** 2026-01-19

---

## Problem

The Kalshi API client (`src/kalshi_research/api/client.py`) has ~30 methods that are implemented but never called:

```
get_events (500)
get_event_metadata (574)
get_event_candlesticks (579)
get_multivariate_events (630)
get_multivariate_event_collections (676)
get_multivariate_event_collection (708)
get_tags_by_categories (718)
get_filters_by_sport (727)
get_structured_targets (732)
get_structured_target (760)
get_series_list (765)
get_series (792)
get_series_fee_changes (805)
get_exchange_schedule (816)
get_exchange_announcements (821)
get_user_data_timestamp (826)
get_milestones (833)
get_milestone (877)
get_milestone_live_data (882)
get_live_data_batch (887)
get_incentive_programs (896)
lookup_multivariate_event_collection_tickers (1030)
get_orders (1113)
batch_create_orders (1201)
batch_cancel_orders (1257)
decrease_order (1311)
get_order_queue_position (1378)
get_orders_queue_positions (1384)
get_total_resting_order_value (1404)
get_order_groups (1412)
create_order_group (1417)
get_order_group (1469)
reset_order_group (1474)
delete_order_group (1514)
```

---

## Analysis

### Trading Methods (Keep - Safety Critical)
These exist for future TradeExecutor integration:
- `batch_create_orders`, `batch_cancel_orders`, `decrease_order`
- Order group methods
- Queue position methods

**Decision:** Keep. Will be needed when execution is enabled.

### Discovery Methods (Evaluate)
- `get_events`, `get_multivariate_events` - possibly useful for market discovery
- `get_tags_by_categories`, `get_filters_by_sport` - discovery helpers
- `get_structured_targets` - unclear use case

**Decision:** Keep for now. Low cost, potential future use.

### Informational Methods (Evaluate)
- `get_exchange_schedule`, `get_exchange_announcements` - useful for status
- `get_milestones`, `get_incentive_programs` - gamification, not core

**Decision:** Keep schedule/announcements. Consider removing milestone/incentive if truly unused.

---

## Options

### Option A: Keep All (Current State)
Rationale: API completeness. Low maintenance cost.

### Option B: Prune Unused Methods
Remove methods that:
1. Have no foreseeable use case
2. Are not trading-related (safety)
3. Are not documented in any spec/future item

### Option C: Mark as Public API
Add docstrings explicitly marking these as "available for programmatic use" to silence vulture warnings.

---

## Rob C. Martin Principle

YAGNI (You Ain't Gonna Need It) - Don't implement features until needed.

Counter-argument: These ARE the Kalshi API. Having full coverage isn't speculation, it's completeness.

---

## Recommendation

**Keep trading methods.** These will be used.

**Review discovery/info methods.** If no CLI command or spec references them, consider removal in a cleanup pass.

---

## Acceptance Criteria

- [ ] Each unused method either:
  - Has a documented use case (spec, future item, or docstring), OR
  - Is removed
- [ ] Trading methods are explicitly kept and documented
- [ ] Vulture warnings addressed (either removal or whitelist)

---

## References

- `src/kalshi_research/api/client.py`
- Vulture audit output
- [FUTURE-002: Kalshi Blocked Endpoints](../_future/FUTURE-002-kalshi-blocked-endpoints.md)
