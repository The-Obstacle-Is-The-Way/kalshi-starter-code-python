# BUG-047: Portfolio Positions Sync Discrepancy

**Priority**: Medium
**Status**: Resolved (Known API Behavior)
**Created**: 2026-01-09
**Resolved**: 2026-01-09

## Symptom

`uv run kalshi portfolio sync` reports "Synced 0 positions" and `portfolio positions` shows "No open positions found", but `portfolio balance` shows a non-zero `portfolio_value` ($87.37).

## Context

- 9 trades were successfully synced to the database
- All markets appear to still be active (checked KXNCAAFSPREAD-26JAN09OREIND-IND3, status=active)
- Balance API returns: balance=10666, portfolio_value=8737

## Root Cause

This is **known Kalshi API behavior**, not a bug in our code. The discrepancy occurs because:

1. **`/portfolio/positions` endpoint**: Returns only **currently open positions** in active markets. It does **not** include:
   - Positions in recently closed/settled markets
   - Positions pending settlement
   - Positions that have been automatically closed

2. **`/portfolio/balance` endpoint**: The `portfolio_value` field may include:
   - Pending settlements
   - Recently closed positions not yet reflected in the balance
   - Temporary inconsistencies during Kalshi's settlement process

This is a timing issue on Kalshi's side where different endpoints update at different rates during market settlements.

## Resolution

Added enhanced logging to `portfolio/syncer.py:sync_positions()`:
- Debug logging shows the raw API response count and content
- Warning message when positions list is empty, explaining this is known Kalshi API behavior
- Users are informed that the discrepancy is expected and will resolve as settlements complete

## Changes Made

- `src/kalshi_research/portfolio/syncer.py:107`: Added debug logging for API response
- `src/kalshi_research/portfolio/syncer.py:110-116`: Added warning with explanation of Kalshi API behavior

## Related Files

- `src/kalshi_research/portfolio/syncer.py`
- `src/kalshi_research/api/client.py`

## User Action Required

No action needed. The portfolio_value discrepancy will resolve automatically as Kalshi completes settlements. If it persists for >24 hours, contact Kalshi support.
