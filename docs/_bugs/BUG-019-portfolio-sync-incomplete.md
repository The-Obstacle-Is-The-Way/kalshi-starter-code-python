# BUG-019: Portfolio Sync Implementation Incomplete

## Priority
P3 (Medium) - Feature Missing

## Description
The `PortfolioSyncer` class contains `TODO` comments and commented-out code for its core functionality: syncing positions and trades. The methods `sync_positions` and `sync_trades` currently return hardcoded `0` values.

## Location
- `src/kalshi_research/portfolio/syncer.py`: Lines 39-41, 54-56.

## Impact
- **Functionality:** Users cannot track their portfolio, P&L, or trade history.
- **Misleading UI:** The CLI might report "Success" for sync operations that actually did nothing.

## Proposed Fix
1. Implement the `get_positions` and `get_fills` methods in `KalshiClient`.
2. Uncomment and finalize the logic in `PortfolioSyncer`.
3. Add integration tests to verify data is correctly saved to the `positions` and `trades` tables.
