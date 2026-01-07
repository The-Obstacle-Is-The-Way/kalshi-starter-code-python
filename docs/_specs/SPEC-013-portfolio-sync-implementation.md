# SPEC-013: Portfolio Synchronization Implementation

## Status
Proposed

## Context
The platform currently lacks the ability to sync user portfolio data (positions and trades) from Kalshi. This is a critical feature for P&L tracking, thesis validation, and historical analysis. The `PortfolioSyncer` class exists as a stub (BUG-019).

## Goals
1.  Implement robust synchronization of current positions.
2.  Implement synchronization of trade history (fills).
3.  Link trades to positions where possible.
4.  Ensure idempotency (don't duplicate trades).

## Technical Design

### 1. API Client Updates
The `KalshiClient` (authenticated) needs to expose the `fills` endpoint.

```python
class KalshiClient(KalshiPublicClient):
    # ...
    async def get_fills(
        self,
        ticker: str | None = None,
        min_ts: int | None = None,
        max_ts: int | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Fetch matched trades (fills)."""
        # GET /portfolio/fills
        pass
```

### 2. Position Sync Logic
- **Endpoint:** `GET /portfolio/positions`
- **Behavior:**
    - Fetch all `market_positions`.
    - For each position:
        - Check if it exists in DB (match by `ticker`).
        - If exists: Update `quantity`, `avg_price`, `current_price`, `last_synced`.
        - If new: Insert new `Position` record.
    - **Handling Closed Positions:** If a position is in the DB but NOT in the API response (and `quantity > 0` in DB), mark it as closed (update `closed_at`, set `quantity=0`).

### 3. Trade Sync Logic
- **Endpoint:** `GET /portfolio/fills`
- **Behavior:**
    - Fetch fills incrementally (using `min_ts` from the last synced trade).
    - **Idempotency:** Use `kalshi_trade_id` (from API `trade_id`) to prevent duplicates.
    - For each new fill:
        - Insert into `trades` table.
        - `action` is derived from `side` and `is_taker` (or explicit API field if available).
        - `total_cost_cents` = `price * quantity`.

### 4. Data Mapping
| API Field | DB Field (`Position`) | Notes |
|Or|---|---|
| `ticker` | `ticker` | |
| `position` | `quantity` | |
| `fees_paid` | N/A | Stored in trades? |
| `realized_pnl` | `realized_pnl_cents` | |

| API Field | DB Field (`Trade`) | Notes |
|---|---|---|
| `trade_id` | `kalshi_trade_id` | Unique key |
| `ticker` | `ticker` | |
| `count` | `quantity` | |
| `yes_price` | `price_cents` | |
| `action` | `action` | buy/sell |
| `created_time` | `executed_at` | |

## Database Changes
No schema changes required. Existing `positions` and `trades` tables in `src/kalshi_research/portfolio/models.py` are sufficient.

## Security
- API keys are already handled by `KalshiClient`.
- No new secrets required.

## Testing
- Integration tests using `respx` to mock Kalshi API responses.
- Verify that repeated syncs do not duplicate data.
