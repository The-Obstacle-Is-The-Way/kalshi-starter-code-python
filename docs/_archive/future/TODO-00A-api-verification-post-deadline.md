# TODO-00A: Verify API After Jan 15 Deadline

**Priority**: Medium
**Status**: ✅ Complete
**Created**: 2026-01-09
**Completed**: 2026-01-15
**Blocking Condition**: ~~Kalshi API deadline has not passed yet~~ **RESOLVED**

---

## Overview

Verify that the cent-to-dollar field migration (TODO-009) works correctly against the live Kalshi API after the January 15, 2026 deprecation deadline.

## Why Blocked?

The old cent-denominated fields (`yes_bid`, `yes_ask`, etc.) will be **removed** from the API on January 15, 2026. Until that date:

- We cannot verify the migration works with real API data
- The API still returns both old and new fields
- Testing now would give false confidence

## When to Unblock

**Date**: January 15, 2026 or later

After this date:
1. Run integration tests against live API
2. Verify `*_dollars` fields parse correctly
3. Confirm computed properties (`yes_bid_cents`, etc.) work
4. Check that no code depends on removed fields

## Verification Checklist

**Verified on 2026-01-15:**

- [x] `kalshi market get <ticker>` shows correct prices ✅
- [x] `kalshi scan opportunities` works without errors ✅
- [x] Portfolio sync handles new field format ✅
- [x] Live API endpoint testing: 19/19 endpoints pass ✅
- [x] All unit tests pass (201 tests) ✅
- [x] No ValidationError from Pydantic on real API data ✅

**Details:**
- Ran comprehensive live API test script covering all Phase 1-4 endpoints
- Fixed 3 model bugs discovered during testing (nullable fields): `EventMetadataResponse.market_details`, `EventMetadataResponse.settlement_sources`, `GetOrderQueuePositionsResponse.queue_positions`
- All `*_dollars` fields parse correctly; cent fields successfully deprecated
- See DEBT-028 for full migration documentation

## Related

- [TODO-009 (Archived)](../_archive/future/TODO-009-cent-field-deprecation-migration.md) - Migration implementation
- [Kalshi API Changelog](https://docs.kalshi.com/changelog) - Breaking changes

---

**Note**: This is a placeholder TODO (00A series) for work that is blocked by external factors. When the blocking condition is resolved, create a proper TODO-XXX and archive this placeholder.
