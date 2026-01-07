# Kalshi Official API Reference (2026)

**Source:** [docs.kalshi.com](https://docs.kalshi.com/welcome)
**Last Updated:** 2026-01-07

---

## Authentication

### API Key Types
- **Generate API Key**: Platform creates RSA key pair, returns private key once
- **Create API Key**: Provide your own RSA public key (Premier/Market Maker tier)

### Key Usage
API keys allow programmatic access without username/password authentication.

---

## Rate Limits

| Tier | Read Limit | Write Limit | Qualification |
|------|-----------|------------|---------------|
| **Basic** | 20/sec | 10/sec | Completing signup |
| **Advanced** | 30/sec | 30/sec | Complete [Advanced API form](https://kalshi.typeform.com/advanced-api) |
| **Premier** | 100/sec | 100/sec | 3.75% of exchange volume/month + technical competency |
| **Prime** | 400/sec | 400/sec | 7.5% of exchange volume/month + technical competency |

### Write-Limited Operations
Only these endpoints count against write limits:
- `BatchCreateOrders` (each item = 1 transaction)
- `BatchCancelOrders` (each cancel = 0.2 transactions)
- `CreateOrder`, `CancelOrder`, `AmendOrder`, `DecreaseOrder`

### Open Order Limit
- **Maximum**: 200,000 open orders per user

---

## Pagination

### Cursor-Based Pagination
All list endpoints use cursor-based pagination:
- **`limit`**: Page size (1-1000, default: 100)
- **`cursor`**: Pass from previous response to get next page
- **Empty cursor**: Indicates no more pages

### Best Practices
1. Use maximum `limit=1000` to reduce API calls
2. Monitor for empty cursor to detect completion
3. Consider rate limits when paginating large datasets

---

## REST API Endpoints

### Market Data (No Auth Required)

| Endpoint | Description |
|----------|-------------|
| `GET /markets` | List markets with filters |
| `GET /markets/{ticker}` | Single market details |
| `GET /markets/{ticker}/orderbook` | Current order book |
| `GET /markets/trades` | Historical trades (paginated) |
| `GET /series/{ticker}` | Series template information |
| `GET /events` | List events (excludes multivariate) |
| `GET /events/multivariate` | Multivariate events only |
| `GET /events/{ticker}` | Single event details |
| `GET /events/{ticker}/metadata` | Event metadata |

### GET /markets Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter: `unopened`, `open`, `closed`, `settled` |
| `limit` | int | Page size (1-1000, default: 100) |
| `cursor` | string | Pagination cursor |
| `min_created_ts` / `max_created_ts` | datetime | Creation time filter |
| `min_close_ts` / `max_close_ts` | datetime | Close time filter (requires status=closed) |
| `min_settled_ts` / `max_settled_ts` | datetime | Settlement time filter (requires status=settled) |

**Note**: Timestamp filters are mutually exclusive.

### Orders (Authenticated)

| Endpoint | Description |
|----------|-------------|
| `POST /portfolio/orders` | Create single order |
| `POST /portfolio/orders/batched` | Create up to 20 orders |
| `GET /portfolio/orders` | List orders by status |
| `DELETE /portfolio/orders/{id}` | Cancel order |
| `POST /portfolio/orders/{id}/amend` | Modify price/quantity |
| `GET /portfolio/orders/{id}/queue_position` | Queue position |

### Portfolio (Authenticated)

| Endpoint | Description |
|----------|-------------|
| `GET /portfolio/balance` | Account balance (in cents) |
| `GET /portfolio/positions` | Holdings across markets |
| `GET /portfolio/fills` | Trade history |
| `GET /portfolio/settlements` | Settlement records |

---

## WebSocket API

### Connection
Single WebSocket endpoint for all real-time communication.

### Keep-Alive
- Kalshi sends **Ping frames (0x9)** every 10 seconds with body `heartbeat`
- Clients must respond with **Pong frames (0xA)**

### Available Channels

| Channel | Auth Required | Description |
|---------|---------------|-------------|
| `orderbook_delta` | No | Real-time orderbook changes |
| `ticker` | No | Price, volume, open interest updates |
| `trade` | No | Public trade notifications |
| `fill` | Yes | Your order fill notifications |
| `market_positions` | Yes | Real-time position updates |
| `market_lifecycle_v2` | No | Market state changes |
| `multivariate` | No | Multivariate collection notifications |
| `communications` | Yes | RFQ/quote notifications |

### Channel Filtering
- **Single market**: `market_ticker` (string)
- **Multiple markets**: `market_tickers` (array)
- **Omit**: Receive all available data

### Value Format
- WebSocket monetary values are in **centi-cents** (1/10,000th of a dollar)
- Divide by 10,000 to convert to dollars

---

## FIX Protocol

For institutional traders and high-frequency operations:
- **Protocol**: FIX 4.4
- **Use case**: Professional trading organizations
- **Setup**: More complex than REST/WebSocket

---

## Demo Environment

Available for testing before production:
- Configure base URL to demo endpoint
- Use test credentials
- Safe sandbox for integration testing

---

## Developer Resources

- **Official Docs**: https://docs.kalshi.com/welcome
- **Help Center**: https://help.kalshi.com/kalshi-api
- **Discord**: `#dev` channel for developer support
- **Python SDK**: `kalshi-python` on PyPI
- **OpenAPI Spec**: Available for download

---

## Key Concepts

| Term | Definition |
|------|------------|
| **Market** | Binary yes/no outcome within an event |
| **Event** | Collection of related markets |
| **Series** | Template for recurring events |
| **Fill** | Completed trade transaction |
| **Queue Position** | Contracts ahead before your order fills |
| **Orderbook** | Yes bids and no bids (binary structure) |
