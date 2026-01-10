# Kalshi Official API Reference (2026)

**Source:** [docs.kalshi.com](https://docs.kalshi.com/welcome)
**OpenAPI Spec:** [docs.kalshi.com/openapi.yaml](https://docs.kalshi.com/openapi.yaml)
**Last Verified:** 2026-01-10

---

## Base URLs

| Environment | REST API | WebSocket |
|-------------|----------|-----------|
| **Production** | `https://api.elections.kalshi.com/trade-api/v2` | `wss://api.elections.kalshi.com/trade-api/ws/v2` |
| **Demo** | `https://demo-api.kalshi.co/trade-api/v2` | `wss://demo-api.kalshi.co/trade-api/ws/v2` |

> **Note:** Despite the "elections" subdomain, the production API serves ALL Kalshi markets (economics, climate, tech, entertainment, etc.).

---

## Authentication (REST + WebSocket)

### Required Headers

| Header | Description |
|--------|-------------|
| `KALSHI-ACCESS-KEY` | Your API Key ID (UUID format) |
| `KALSHI-ACCESS-TIMESTAMP` | Unix timestamp in **milliseconds** |
| `KALSHI-ACCESS-SIGNATURE` | Base64-encoded RSA-PSS signature |

### Signature Algorithm

```
Message to sign: {timestamp}{HTTP_METHOD}{path}
Algorithm: RSA-PSS with SHA-256
Salt Length: PSS.DIGEST_LENGTH
Output: Base64 string
```

**CRITICAL:** The `path` **excludes query parameters**.

| Request | Signature Message |
|---------|-------------------|
| `GET /portfolio/orders?limit=5` | `1703123456789GET/trade-api/v2/portfolio/orders` |
| `POST /portfolio/orders` | `1703123456789POST/trade-api/v2/portfolio/orders` |
| WebSocket connect | `1703123456789GET/trade-api/ws/v2` |

### API Key Scopes (Dec 2025+)

Keys now support `scopes` field with `read` and `write` permissions.

---

## Rate Limits

| Tier | Read/sec | Write/sec | Qualification |
|------|----------|-----------|---------------|
| **Basic** | 20 | 10 | Completing signup |
| **Advanced** | 30 | 30 | [Advanced API form](https://kalshi.typeform.com/advanced-api) |
| **Premier** | 100 | 100 | 3.75% monthly exchange volume + technical competency |
| **Prime** | 400 | 400 | 7.5% monthly exchange volume + technical competency |

### Write-Limited Operations ONLY

Only these count against **write** limits:

| Operation | Cost |
|-----------|------|
| `CreateOrder` | 1 transaction |
| `BatchCreateOrders` | 1 transaction per order item |
| `CancelOrder` | 1 transaction |
| `BatchCancelOrders` | 0.2 transactions per cancel |
| `AmendOrder` | 1 transaction |
| `DecreaseOrder` | 1 transaction |

### Open Order Limit

**Maximum:** 200,000 open orders per user

---

## Pagination

### Cursor-Based Pagination

| Parameter | Description |
|-----------|-------------|
| `limit` | Page size (endpoint-specific default; commonly 100; endpoint-specific max) |
| `page_size` | Page size for `GET /structured_targets` (default: 100; max: 2000) |
| `cursor` | Pass from previous response to get next page |

**Continue until `cursor` is null/empty/missing.**

### Maximum Limits by Endpoint

| Endpoint | Page Size Param | Max |
|----------|------------------|-----|
| `GET /markets` | `limit` | 1000 |
| `GET /markets/trades` | `limit` | 1000 |
| `GET /events` | `limit` | 200 |
| `GET /events/multivariate` | `limit` | 200 |
| `GET /structured_targets` | `page_size` | 2000 |

---

## REST API Endpoints

### Exchange (No Auth)

| Endpoint | Description |
|----------|-------------|
| `GET /exchange/status` | Exchange status (`exchange_active`, `trading_active`) |
| `GET /exchange/announcements` | Exchange-wide announcements |
| `GET /exchange/schedule` | Trading schedule |
| `GET /exchange/fee` | Fee change schedule |
| `GET /exchange/user_data_timestamp` | User data timestamp |

### Market Data (No Auth)

| Endpoint | Description |
|----------|-------------|
| `GET /markets` | List markets with filters |
| `GET /markets/{ticker}` | Single market details |
| `GET /markets/{ticker}/orderbook` | Current orderbook |
| `GET /markets/{ticker}/candlesticks` | OHLC candlestick data |
| `GET /markets/candlesticks` | Batch candlesticks (multiple markets) |
| `GET /markets/trades` | Historical trades (paginated) |
| `GET /series` | List series templates |
| `GET /series/{ticker}` | Single series details |
| `GET /events` | List events (**excludes multivariate**) |
| `GET /events/multivariate` | Multivariate events only |
| `GET /events/{ticker}` | Single event details |
| `GET /events/{ticker}/metadata` | Event metadata |
| `GET /events/{ticker}/candlesticks` | Event-level candlestick data |
| `GET /events/{ticker}/forecast_percentiles_history` | Forecast percentile history |
| `GET /structured_targets` | List structured targets (cursor + `page_size`) |
| `GET /structured_targets/{structured_target_id}` | Structured target details |

> **Docs conflict (market data auth):** Kalshi’s quickstart docs describe market-data REST endpoints as public, but
> the OpenAPI spec marks some (notably orderbook) as requiring auth headers. As of 2026-01-08, unauthenticated
> `GET /markets/{ticker}/orderbook` works in practice; if you see 401s, retry with signed headers.

### GET /markets Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | enum | `unopened`, `open`, `paused`, `closed`, `settled` |
| `tickers` | string | Comma-separated market tickers |
| `event_ticker` | string | Filter by event (up to 10 comma-separated) |
| `series_ticker` | string | Filter by series |
| `mve_filter` | enum | `only` (multivariate only) or `exclude` (no multivariate) |
| `limit` | int | Page size (1-1000, default: 100) |
| `cursor` | string | Pagination cursor |
| `min_created_ts` / `max_created_ts` | int | Unix timestamp filters |
| `min_close_ts` / `max_close_ts` | int | Close time filters |
| `min_settled_ts` / `max_settled_ts` | int | Settlement time filters |

**Note:** Timestamp filters are mutually exclusive. Only one status filter allowed.

### Market Response Settlement Fields (Dec 25, 2025+)

| Field | Type | Description |
|-------|------|-------------|
| `settlement_ts` | datetime (RFC3339) | Actual settlement timestamp. **Only populated for settled markets.** |
| `settlement_value` | int | Settlement value in cents for YES side |
| `settlement_value_dollars` | string | Settlement value in dollars (e.g., `"1.00"`) |
| `settlement_timer_seconds` | int | Duration before market settles after determination |

> **Note:** `settlement_ts` is the **actual** settlement time (changelog entry Dec 19, 2025; release date Dec 25, 2025). Prior to this field, `expiration_time` was used as a proxy, which was inaccurate for markets that settled early (event resolved before expiration) or late (disputes, delays).

### Market Provisional Flag (Jan 9, 2025+)

| Field | Type | Description |
|-------|------|-------------|
| `is_provisional` | bool | If `true`, market will be removed if no trading activity occurs by settlement |

> **Note:** Provisional markets are placeholders that may be deleted. Check this flag before building long-term tracking.

### Market status gotcha (filter vs response)

- Query filter (`GET /markets?status=...`): `unopened`, `open`, `paused`, `closed`, `settled`
- Market object field (`market.status` in responses): `initialized`, `inactive`, `active`, `closed`, `determined`,
  `disputed`, `amended`, `finalized`

### Orders (Authenticated)

| Endpoint | Description |
|----------|-------------|
| `POST /portfolio/orders` | Create single order |
| `POST /portfolio/orders/batched` | Create up to 20 orders |
| `GET /portfolio/orders` | List orders by status |
| `GET /portfolio/orders/{id}` | Single order details |
| `DELETE /portfolio/orders/{id}` | Cancel order |
| `POST /portfolio/orders/{id}/amend` | Modify price/quantity |
| `POST /portfolio/orders/{id}/decrease` | Decrease order size |
| `GET /portfolio/orders/{id}/queue_position` | Queue position for one order |
| `GET /portfolio/orders/queue_positions` | Queue positions for multiple orders |

### Portfolio (Authenticated)

| Endpoint | Description |
|----------|-------------|
| `GET /portfolio/balance` | Account balance (`balance` + `portfolio_value` in cents) |
| `GET /portfolio/positions` | Holdings across markets |
| `GET /portfolio/fills` | Trade history |
| `GET /portfolio/settlements` | Settlement records (includes trade fees, event ticker) |
| `GET /portfolio/total_resting_order_value` | Total value of resting orders |

### `GET /portfolio/positions` response keys

Kalshi returns both market-level and event-level aggregates:

```json
{
  "cursor": null,
  "market_positions": [
    {
      "ticker": "KX...",
      "position": 34,
      "market_exposure": 952,
      "market_exposure_dollars": "9.52",
      "realized_pnl": 0,
      "fees_paid": 48,
      "fees_paid_dollars": "0.48",
      "total_traded": 34,
      "total_traded_dollars": "14.00",
      "resting_orders_count": 0,
      "last_updated_ts": 1704067200
    }
  ],
  "event_positions": [
    {
      "event_ticker": "KX...",
      "event_exposure": 952,
      "event_exposure_dollars": "9.52",
      "realized_pnl": 0,
      "fees_paid": 48,
      "total_cost": 1400,
      "total_cost_dollars": "14.00",
      "total_cost_shares": 34
    }
  ]
}
```

Implementation note: `KalshiClient.get_positions()` consumes `market_positions` (fallback: legacy `positions`).

> **💡 Key insight:** The `realized_pnl` field is computed BY KALSHI and includes all closed trades + settlements. For total realized P&L, use this value instead of computing your own FIFO. Only compute per-trade FIFO if you need win/loss breakdowns.

### `GET /portfolio/fills` response fields

**Query Parameters:**

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `limit` | int | 100 | 200 | Results per page |
| `cursor` | string | - | - | Pagination cursor |
| `min_ts` | int64 | - | - | Unix timestamp filter (after) |
| `max_ts` | int64 | - | - | Unix timestamp filter (before) |
| `ticker` | string | - | - | Filter by market |
| `order_id` | string | - | - | Filter by order |

**Response fields (per fill):**

| Field | Type | Description |
|-------|------|-------------|
| `fill_id` | string | Unique fill identifier |
| `trade_id` | string | Legacy field (same as fill_id) |
| `order_id` | string | Parent order ID |
| `ticker` | string | Market ticker |
| `side` | enum | `yes` or `no` - **literal side, not effective position** |
| `action` | enum | `buy` or `sell` |
| `count` | int | Contracts filled |
| `yes_price` | int | YES price in cents |
| `no_price` | int | NO price in cents |
| `yes_price_fixed` | string | YES price in dollars (e.g., `"0.48"`) |
| `no_price_fixed` | string | NO price in dollars (e.g., `"0.52"`) |
| `is_taker` | bool | True if removed liquidity |
| `client_order_id` | string | Client-provided order ID (if set) |
| `created_time` | string | RFC3339 timestamp |

> **⚠️ Data Retention:** Kalshi does NOT document how far back fills history is retained. Do not assume complete history exists.

> **⚠️ Cross-Side Closing:** The `side` field is **literal** (the side you traded), NOT the effective position side. Selling YES to close a NO position shows `side=yes`, which can confuse FIFO calculations.

> **Note:** Market settlements appear in `/portfolio/settlements`, NOT `/portfolio/fills`. For complete P&L, you need both endpoints.

---

## Orderbook Endpoint

### GET /markets/{ticker}/orderbook

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `depth` | integer | 0 | Depth of orderbook (0 or negative = all levels, 1-100 for specific depth) |

### Response Format

```json
{
  "orderbook": {
    "yes": [[price_cents, count], ...],
    "no": [[price_cents, count], ...],
    "yes_dollars": [["0.1500", count], ...],
    "no_dollars": [["0.8500", count], ...]
  }
}
```

- **Integer fields:** Cents (0-100 scale, $0.00-$1.00)
- **Dollar fields:** String format like `"0.1500"`
- **Levels:** Sorted best-to-worst price (highest bid first)
- **Empty sides:** Arrays omitted when no orders exist

**Binary market math:** A YES bid at price X = NO ask at price (100-X)

> **Note:** The orderbook shows **bids only** for both sides. YES asks are implied from NO bids (and vice versa). A yes bid at 7¢ = no ask at 93¢.

---

## WebSocket API

### Connection Authentication

**ALL WebSocket connections require authentication**, even for public data channels.

Use the same three headers as REST:
- `KALSHI-ACCESS-KEY`
- `KALSHI-ACCESS-TIMESTAMP`
- `KALSHI-ACCESS-SIGNATURE` (sign: `{timestamp}GET/trade-api/ws/v2`)

### Keep-Alive

- Kalshi sends **Ping frames (0x9)** every ~10 seconds with body `heartbeat`
- Clients must respond with **Pong frames (0xA)**

### Subscribe Command

```json
{
  "id": 1,
  "cmd": "subscribe",
  "params": {
    "channels": ["ticker"],
    "market_tickers": ["KXBTC-25JAN-T100000"]
  }
}
```

`params` supports either `market_ticker` (single) or `market_tickers` (list).

Other commands: `unsubscribe`, `list_subscriptions`, `update_subscription`

### Available Channels

| Channel | Data Scope | Description |
|---------|------------|-------------|
| `orderbook_delta` | Public | Orderbook changes (requires market filter) |
| `ticker` | Public | Price, volume, open interest updates |
| `trade` | Public | Public trade notifications |
| `market_lifecycle_v2` | Public | Market state changes, event creation |
| `multivariate` | Public | Multivariate collection notifications |
| `fill` | Private | Your order fills (market filter ignored) |
| `market_positions` | Private | Your position updates |
| `communications` | Private | RFQ and quote notifications |

### orderbook_delta Channel Details

**Subscription:**
```json
{
  "id": 2,
  "cmd": "subscribe",
  "params": {
    "channels": ["orderbook_delta"],
    "market_tickers": ["KXBTC-26JAN15-T100000"]
  }
}
```

**Initial Snapshot (sent first):**
```json
{
  "type": "orderbook_snapshot",
  "sid": 2,
  "seq": 2,
  "msg": {
    "market_ticker": "KXBTC-26JAN15-T100000",
    "yes": [[47, 300], [46, 150]],
    "yes_dollars": [["0.470", 300], ["0.460", 150]],
    "no": [[53, 200], [54, 100]],
    "no_dollars": [["0.530", 200], ["0.540", 100]]
  }
}
```

**Delta Updates (incremental):**
```json
{
  "type": "orderbook_delta",
  "sid": 2,
  "seq": 3,
  "msg": {
    "market_ticker": "KXBTC-26JAN15-T100000",
    "price": 47,
    "price_dollars": "0.470",
    "delta": -50,
    "side": "yes"
  }
}
```

| Field | Description |
|-------|-------------|
| `seq` | Sequence number for ordering and gap detection |
| `delta` | Change in quantity (positive = add, negative = remove) |
| `side` | `"yes"` or `"no"` |

**Applying deltas:** Update quantity at price level. Remove level when quantity reaches 0. Track `seq` to detect missed messages.

### Price/Value Units

**CRITICAL: Units vary by channel!**

| Channel/Field | Unit | Conversion |
|---------------|------|------------|
| `ticker.price`, `ticker.yes_bid`, `ticker.yes_ask` | **Cents** | Divide by 100 for dollars |
| `ticker.price_dollars`, `ticker.yes_bid_dollars` | **Dollars (string)** | Direct use |
| `orderbook_delta.price` | **Cents** | Divide by 100 for dollars |
| `market_positions.position_cost` | **Centi-cents** | Divide by 10,000 for dollars |
| `market_positions.realized_pnl` | **Centi-cents** | Divide by 10,000 for dollars |
| `market_positions.fees_paid` | **Centi-cents** | Divide by 10,000 for dollars |

**Example conversion:**
- Ticker `price: 48` → $0.48
- Position `position_cost: 500000` → $50.00

### Ticker Channel Additional Fields

The `ticker` channel includes fields not always documented:

| Field | Type | Description |
|-------|------|-------------|
| `dollar_volume` | string | Volume in dollars |
| `dollar_open_interest` | string | Open interest in dollars |
| `no_bid_dollars` | string | NO bid price in dollars |
| `ts` | int | Unix timestamp of tick |

### Update Subscription Command

Modify existing subscriptions without full resubscribe:

```json
{
  "id": 5,
  "cmd": "update_subscription",
  "params": {
    "sid": 2,
    "action": "add_markets",
    "market_tickers": ["KXBTC-26FEB01"]
  }
}
```

| Parameter | Description |
|-----------|-------------|
| `sid` / `sids` | Single subscription ID or array of IDs |
| `action` | `add_markets` or `delete_markets` |
| `market_tickers` | Markets to add/remove |

### WebSocket Error Codes

| Code | Error | Description |
|------|-------|-------------|
| 1 | Unable to process message | General processing error |
| 2 | Params required | Missing params object |
| 3 | Channels required | Missing channels array |
| 4 | Subscription IDs required | Missing sids in unsubscribe |
| 5 | Unknown command | Invalid command name |
| 7 | Unknown subscription ID | Subscription ID not found |
| 8 | Unknown channel name | Invalid channel |
| 9 | Authentication required | Private channel without auth |
| 10 | Channel error | Channel-specific error |
| 11 | Invalid parameter | Malformed parameter value |
| 12 | Exactly one subscription ID required | For update_subscription |
| 13 | Unsupported action | Invalid action |
| 14 | Market ticker required | Missing market specification |
| 15 | Action required | Missing action in update_subscription |
| 16 | Market not found | Invalid market ticker |
| 17 | Internal error | Server-side processing error |

---

## SDKs

### Python (Current)

```bash
pip install kalshi-python-sync   # Synchronous
pip install kalshi-python-async  # Asynchronous
```

> **Note:** pip normalizes underscores to hyphens. The actual package names use hyphens (`kalshi-python-sync`),
> but imports use underscores (`import kalshi_python_sync`). Kalshi docs show both conventions.

> **Docs conflict:** Kalshi's Python SDK docs currently have both `kalshi-python` and the newer
> `kalshi_python_sync` / `kalshi_python_async` pages live. The quickstart calls `kalshi-python` deprecated.

### TypeScript/JavaScript

```bash
npm install kalshi-typescript
```

---

## FIX Protocol

For institutional traders and high-frequency operations:
- **Protocol:** FIX 4.4
- **Access:** Gated (contact Kalshi)
- **Docs:** `docs.kalshi.com/fix`

---

## Additional Endpoints (Less Common)

These endpoints exist in the API but are less commonly used:

### Order Groups (Authenticated)

Manage groups of orders that can be modified/canceled together:

| Endpoint | Description |
|----------|-------------|
| `GET /order_groups` | List order groups |
| `POST /order_groups` | Create order group |
| `GET /order_groups/{id}` | Get order group details |
| `DELETE /order_groups/{id}` | Delete order group |
| `PUT /order_groups/{id}/reset` | Reset order group |

### Milestones (No Auth)

| Endpoint | Description |
|----------|-------------|
| `GET /milestones` | List milestones |
| `GET /milestones/{id}` | Get milestone details |

### Live Data (No Auth)

| Endpoint | Description |
|----------|-------------|
| `GET /live_data/{type}` | Get live data by type |
| `GET /live_data/batch` | Batch live data |

### Incentive Programs (Authenticated)

| Endpoint | Description |
|----------|-------------|
| `GET /incentive_programs` | List incentive programs |

### FCM (Futures Commission Merchant)

| Endpoint | Description |
|----------|-------------|
| `GET /fcm/orders` | FCM orders |
| `GET /fcm/positions` | FCM positions |

### API Keys Management (Authenticated)

| Endpoint | Description |
|----------|-------------|
| `GET /api_keys` | List API keys |
| `POST /api_keys` | Create API key |
| `POST /api_keys/generate` | Generate new API key |
| `DELETE /api_keys/{id}` | Delete API key |

### Search (No Auth)

| Endpoint | Description |
|----------|-------------|
| `GET /search/tags` | Search tags |
| `GET /search/sports_filters` | Sports filter options |

### Portfolio Settlements (Authenticated)

| Endpoint | Description |
|----------|-------------|
| `GET /portfolio/settlements` | Your settlement history (when markets resolve) |

**Query Parameters:**

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `limit` | int | 100 | 200 | Results per page |
| `cursor` | string | - | - | Pagination cursor |
| `ticker` | string | - | - | Filter by market |
| `event_ticker` | string | - | - | Filter by event (comma-separated, max 10) |
| `min_ts` | int64 | - | - | Unix timestamp filter (after) |
| `max_ts` | int64 | - | - | Unix timestamp filter (before) |

**Response fields (per settlement):**

| Field | Type | Description |
|-------|------|-------------|
| `ticker` | string | Market that settled |
| `event_ticker` | string | Parent event |
| `market_result` | enum | `yes`, `no`, `scalar`, or `void` |
| `yes_count` | int | YES contracts held at settlement |
| `no_count` | int | NO contracts held at settlement |
| `yes_total_cost` | int | Cost basis of YES contracts (cents) |
| `no_total_cost` | int | Cost basis of NO contracts (cents) |
| `revenue` | int | Payout received (100¢ per winning contract) |
| `settled_time` | string | ISO timestamp when settled |
| `fee_cost` | string | Fees in fixed-point dollars |
| `value` | int/null | Payout per contract (for scalar markets) |

> **⚠️ Critical for P&L:** Settlements are NOT fills. When a market settles:
> - Your position auto-closes
> - This appears in `/portfolio/settlements`, NOT `/portfolio/fills`
> - For complete FIFO P&L, you need BOTH endpoints
> - Settlements act as "sells" at the settlement price (100¢ if won, 0¢ if lost)

---

## Create Order Safety Parameters

`POST /portfolio/orders` supports several safety-critical parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `reduce_only` | bool | **SAFETY:** Only reduce position, never increase. Use for closing trades. |
| `cancel_order_on_pause` | bool | Auto-cancel if trading paused on exchange |
| `buy_max_cost` | int | Max cost in cents. Enables Fill-or-Kill behavior. |
| `post_only` | bool | Maker-only order (avoid taker fees, reject if would cross) |
| `self_trade_prevention_type` | enum | `taker_at_cross` or `maker` - prevent self-trades |
| `order_group_id` | string | Link order to a group (grouped cancel/modify) |
| `time_in_force` | enum | `fill_or_kill`, `good_till_canceled`, `immediate_or_cancel` |

### Order Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `queue_position` | int | **DEPRECATED** - Always returns 0. Use `GET /portfolio/orders/{id}/queue_position` instead. |
| `taker_fees_dollars` | string | Fees paid on taker fills (dollars) |
| `maker_fees_dollars` | string | Fees paid on maker fills (dollars) |
| `fill_count` | int | Contracts filled so far |
| `remaining_count` | int | Contracts still resting |

### Deprecated Order Fields

| Deprecated | Replacement |
|------------|-------------|
| `sell_position_floor` | Use `reduce_only: true` instead |

---

## Recent Breaking Changes (2025-2026)

### Market response field removals (release Jan 15, 2026)

> **⚠️ IMMINENT:** These fields are being removed in 5 days (Jan 15, 2026).

Cent-denominated fields being removed from **Market** responses:
- `response_price_units`, `notional_value`, `yes_bid`, `yes_ask`, `no_bid`, `no_ask`, `last_price`,
  `previous_yes_bid`, `previous_yes_ask`, `previous_price`, `liquidity` → Use `*_dollars` equivalents.
- `tick_size` → Use `price_level_structure` and `price_ranges`.

**Known edge case:** The `liquidity` field can return **negative values** (e.g., `-170750`) in some markets.
This is likely a calculation artifact or sentinel value. Since the field is deprecated, treat negative
values as `None`/unknown rather than crashing on validation.

**Dollar replacements (these REMAIN in API):**

| REMOVED (Jan 15) | REMAINS (Use This) | Format |
|------------------|-------------------|--------|
| `yes_bid` | `yes_bid_dollars` | String like `"0.4500"` |
| `yes_ask` | `yes_ask_dollars` | String like `"0.5500"` |
| `no_bid` | `no_bid_dollars` | String like `"0.5500"` |
| `no_ask` | `no_ask_dollars` | String like `"0.4500"` |
| `last_price` | `last_price_dollars` | String |
| `previous_price` | `previous_price_dollars` | String |
| `liquidity` | `liquidity_dollars` | String (current offer value) |
| `notional_value` | `notional_value_dollars` | String |
| `tick_size` | `price_level_structure`, `price_ranges` | Object structure |

> **Clarification:** The `*_dollars` fields are the **replacements that survive**. They are NOT being deprecated - they are the new standard. Only the cent-denominated integer fields are being removed.

### Series volume field (release Jan 15, 2026)

New `include_volume` query parameter on `GET /series` endpoints. When set, returns `volume` field with total contracts traded across all events in the series.

### Market response field removals (release Jan 8, 2026)

- `category`, `risk_limit_cents` removed from Market responses.

### API key scopes (release Dec 18, 2025)

- Keys support `scopes: ["read", "write"]` (defaults to full access if omitted; existing keys have both).

### Multivariate events (release Dec 4, 2025)

- `GET /events` now **excludes** multivariate events
- Use `GET /events/multivariate` for multivariate events
- Use `mve_filter` parameter on `/markets` to filter

### Order semantics (late 2025)

- “Pending” removed from order status enum (expected release Nov 27, 2025).
- Order expiration constraints (`expiration_ts` validation and `immediate_or_cancel` interaction) were announced with a
  TBD release date in the changelog; code defensively.

---

## Key Concepts

| Term | Definition |
|------|------------|
| **Market** | Binary yes/no contract within an event |
| **Event** | Collection of related markets |
| **Series** | Template for recurring events |
| **Multivariate Event** | Event with multiple possible outcomes (combos) |
| **Fill** | Completed trade transaction |
| **Queue Position** | Contracts ahead before your order fills |
| **Cents** | Integer 0-100 representing $0.00-$1.00 |
| **Centi-cents** | Integer where 10,000 = $1.00 (used in WS positions) |

---

## Developer Resources

| Resource | URL |
|----------|-----|
| Official Docs | https://docs.kalshi.com/welcome |
| LLMs.txt (AI Discovery) | https://docs.kalshi.com/llms.txt |
| OpenAPI Spec | https://docs.kalshi.com/openapi.yaml |
| API Changelog | https://docs.kalshi.com/changelog |
| Help Center | https://help.kalshi.com/kalshi-api |
| Discord | `#dev` channel |
| Demo Portal | https://demo.kalshi.co |

> **Tip:** The `llms.txt` file is a standard LLM navigation file that lists all documentation pages. Useful for AI agents exploring the API.
