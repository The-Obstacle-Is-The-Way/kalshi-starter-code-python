# BUG-047: Portfolio Positions Sync Discrepancy

**Priority**: Medium
**Status**: Fixed
**Created**: 2026-01-09
**Resolved**: 2026-01-10

## Symptom

`uv run kalshi portfolio sync` reports "Synced 0 positions" and `kalshi portfolio positions` shows "No open positions found", despite the account having active market positions.

## Context

- `GET /portfolio/positions` returns both market-level and event-level positions.
- Our client code expected the response key `positions`, so it silently parsed an empty list.

## Root Cause

Kalshi returns positions under `market_positions` (and `event_positions`), not `positions`.

Observed live response keys:

```json
{
  "cursor": null,
  "market_positions": [...],
  "event_positions": [...]
}
```

Our implementation in `KalshiClient.get_positions()` incorrectly did:

```python
positions_raw = data.get("positions", [])
```

So `PortfolioSyncer.sync_positions()` always saw `api_positions == []`.

## Resolution

Parse the correct key (`market_positions`) with a backwards-compatible fallback to `positions` for older docs/examples.

## Changes Made

- `src/kalshi_research/api/client.py:552`: `get_positions()` now reads `market_positions` (fallback: `positions`)
- `tests/unit/api/test_client_extended.py:44`: Updated tests to match live API (`market_positions`) and kept a legacy compatibility test

## Related Files

- `src/kalshi_research/portfolio/syncer.py`
- `src/kalshi_research/api/client.py`
- `src/kalshi_research/api/models/portfolio.py`

## User Action Required

Re-run:

```bash
uv run kalshi portfolio sync
uv run kalshi portfolio positions
```

## Acceptance Criteria
- [x] `KalshiClient.get_positions()` parses `market_positions`
- [x] `uv run kalshi portfolio sync` creates/updates DB positions correctly
- [x] `uv run kalshi portfolio positions` shows open positions after sync
