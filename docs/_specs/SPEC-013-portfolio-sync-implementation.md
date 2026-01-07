# SPEC-013: Portfolio Synchronization Implementation

## Status
Implemented (Core). Follow-up: BUG-025.

## Context
The platform supports syncing user portfolio data (positions and fills) from Kalshi into the local SQLite database for downstream P&L, history, and thesis linkage.

## Goals
1. Implement robust synchronization of current positions.
2. Implement synchronization of trade history (fills).
3. Link trades to positions where possible.
4. Ensure idempotency (don't duplicate trades).

## Implementation

### 1. API Client (Authenticated)
`KalshiClient` exposes portfolio endpoints and supports loading private keys from:
- `KALSHI_PRIVATE_KEY_PATH` (PEM file)
- `KALSHI_PRIVATE_KEY_B64` (base64 PEM content; useful for CI)

Relevant methods:
- `KalshiClient.get_positions()` → `GET /portfolio/positions`
- `KalshiClient.get_fills()` → `GET /portfolio/fills` (cursor pagination; `limit` capped to 200)

### 2. Position Sync Logic
- **Endpoint:** `GET /portfolio/positions`
- **Behavior:**
  - Fetch all position dictionaries.
  - For each position:
    - If it exists in DB (match by `ticker`): update `quantity`, `side`, `realized_pnl_cents`, `last_synced`.
    - If new: insert a new `Position` record.
  - **Handling Closed Positions:** if a position is present in DB but absent from API results, mark it closed (`closed_at`, `quantity=0`).

### 3. Trade Sync Logic
- **Endpoint:** `GET /portfolio/fills`
- **Behavior:**
  - Fetch fills via cursor pagination (optionally using `min_ts`).
  - **Idempotency:** use `kalshi_trade_id` (from API `trade_id`) to prevent duplicates.
  - Insert new fills into `trades`.

### 4. Data Mapping
| API Field | DB Field (`Position`) | Notes |
|---|---|---|
| `ticker` | `ticker` | |
| `position` | `quantity` | absolute value stored |
| `realized_pnl` | `realized_pnl_cents` | |

| API Field | DB Field (`Trade`) | Notes |
|---|---|---|
| `trade_id` | `kalshi_trade_id` | unique key |
| `ticker` | `ticker` | |
| `count` | `quantity` | |
| `yes_price` | `price_cents` | |
| `action` | `action` | buy/sell (best-effort) |
| `created_time` | `executed_at` | |

### 5. CLI Wiring
Commands:
- `kalshi portfolio sync --db data/kalshi.db`
- `kalshi portfolio balance`

Required env vars (see `.env.example`):
- `KALSHI_KEY_ID`
- `KALSHI_PRIVATE_KEY_PATH` or `KALSHI_PRIVATE_KEY_B64`
- `KALSHI_ENVIRONMENT` (demo/prod; defaults to demo)

## Database Changes
No schema changes required. Existing `positions` and `trades` tables in `src/kalshi_research/portfolio/models.py` are sufficient.

## Security
- API keys are provided via env and never persisted to disk by the platform.

## Testing
- Unit coverage for sync logic: `tests/unit/portfolio/test_syncer.py`
- CLI smoke coverage: `tests/integration/cli/test_cli_commands.py`
- Live API coverage (skipped by default): `tests/integration/api/test_public_api_live.py`
