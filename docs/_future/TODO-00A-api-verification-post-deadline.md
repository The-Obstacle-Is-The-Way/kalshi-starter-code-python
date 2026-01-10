# TODO-00A: Verify API After Jan 15 Deadline (BLOCKED)

**Priority**: Medium
**Status**: BLOCKED (until Jan 15, 2026)
**Created**: 2026-01-09
**Blocking Condition**: Kalshi API deadline has not passed yet

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

When unblocked, verify:

- [ ] `kalshi market get <ticker>` shows correct prices
- [ ] `kalshi scan opportunities` works without errors
- [ ] Portfolio sync handles new field format
- [ ] All unit tests still pass
- [ ] No ValidationError from Pydantic on real API data

## Related

- [TODO-009 (Archived)](../_archive/future/TODO-009-cent-field-deprecation-migration.md) - Migration implementation
- [Kalshi API Changelog](https://docs.kalshi.com/changelog) - Breaking changes

---

**Note**: This is a placeholder TODO (00A series) for work that is blocked by external factors. When the blocking condition is resolved, create a proper TODO-XXX and archive this placeholder.
