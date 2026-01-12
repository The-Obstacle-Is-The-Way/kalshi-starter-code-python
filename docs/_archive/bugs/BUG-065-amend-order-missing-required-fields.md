# BUG-065: `amend_order()` Missing Required Fields

**Priority:** P2 (UPGRADED - OpenAPI confirms required fields missing)
**Status:** ✅ Fixed
**Found:** 2026-01-12
**Fixed:** 2026-01-12
**Verified:** 2026-01-12 (code audit + live OpenAPI spec fetch)

---

## Summary

The `amend_order()` method was **broken** - it omitted **5 required fields** per the Kalshi OpenAPI
specification, which would cause a **400 Bad Request** / **422 Validation Error** if called against the
real API.

**CRITICAL:** Unlike other "completeness" bugs, this one causes **runtime failures** if the method is ever called with `dry_run=False`.

---

## Fix Implemented

- Updated `KalshiClient.amend_order(...)` to include all required OpenAPI fields:
  - `ticker`, `side`, `action`, `client_order_id`, `updated_client_order_id`
- Removed the incorrect `"order_id": ...` body field (order_id is a path parameter).
- Added support for updating price in either cents (`yes_price`/`no_price`) or dollars
  (`yes_price_dollars`/`no_price_dollars`) with validation that `price` and `price_dollars` are not both
  set.
- Updated unit + integration tests to validate the full payload shape.

---

## OpenAPI Specification Verification

**Source:** `https://docs.kalshi.com/openapi.yaml` (fetched 2026-01-12)

**Endpoint:** `POST /portfolio/orders/{order_id}/amend`

### Required Fields (per OpenAPI spec)

| Field | Type | Description |
|-------|------|-------------|
| `ticker` | string | Market ticker |
| `side` | enum | `"yes"` or `"no"` |
| `action` | enum | `"buy"` or `"sell"` |
| `client_order_id` | string | Original client-specified order ID to be amended |
| `updated_client_order_id` | string | New client-specified order ID after amendment (must be unique) |

### Price Fields (exactly one required)

| Field | Type | Description |
|-------|------|-------------|
| `yes_price` | int | Cents (1-99) |
| `no_price` | int | Cents (1-99) |
| `yes_price_dollars` | string | Dollar format (e.g., `"0.5500"`) |
| `no_price_dollars` | string | Dollar format |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `count` | int | Updated quantity (can increase up to original size) |

---

## Previous Implementation (BROKEN)

### Location

`src/kalshi_research/api/client.py:830-907`

### Current Signature (line 830-836)

```python
async def amend_order(
    self,
    order_id: str,
    price: int | None = None,
    count: int | None = None,
    dry_run: bool = False,
) -> OrderResponse:
```

### Payload Construction (line 874-878)

```python
payload: dict[str, Any] = {"order_id": order_id}
if price is not None:
    payload["yes_price"] = price
if count is not None:
    payload["count"] = count
```

### What Gets Sent to API

```json
{"order_id": "oid-123", "yes_price": 55}
```

### What API Requires

```json
{
  "ticker": "KXMARKET-123",
  "side": "yes",
  "action": "buy",
  "client_order_id": "original-client-id",
  "updated_client_order_id": "new-unique-client-id",
  "yes_price": 55
}
```

### Missing Fields Summary

| Field | Status | Impact |
|-------|--------|--------|
| `ticker` | ❌ Missing | 400/422 error |
| `side` | ❌ Missing | 400/422 error |
| `action` | ❌ Missing | 400/422 error |
| `client_order_id` | ❌ Missing | 400/422 error |
| `updated_client_order_id` | ❌ Missing | 400/422 error |

---

## Unit Test Gap

**Location:** `tests/unit/api/test_trading.py:81-93`

```python
async def test_amend_order(self, mock_client):
    """Verify amend_order payload."""
    mock_client._client.post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"order": {"order_id": "oid-123", "order_status": "executed"}},
    )

    await mock_client.amend_order("oid-123", price=55)

    mock_client._client.post.assert_called_once()
    args, kwargs = mock_client._client.post.call_args
    assert args[0] == "/portfolio/orders/oid-123/amend"
    assert kwargs["json"] == {"order_id": "oid-123", "yes_price": 55}  # Line 93
```

**Problem:** Test mocks the HTTP response, so it passes despite the invalid payload. The test validates our code sends what we *intended*, but what we intended is wrong per the API spec.

---

## Reproduction Steps

1. Create an order via `create_order()` (works fine)
2. Attempt to amend it:
   ```python
   await client.amend_order("order-id-123", price=60)
   ```
3. **Expected:** API returns 400/422 with validation error about missing required fields
4. **Current test behavior:** Passes because HTTP is mocked

---

## Risk Assessment

**Why P2 (upgraded from P3):**
- Method **will fail at runtime** against real API
- Unit test creates false confidence (mocks hide the bug)
- Breaking change to fix (signature must change)

**Current Mitigation:**
- Not exposed via CLI (`grep -r "amend_order" src/kalshi_research/cli/` = no matches)
- Not used in TradeExecutor (`grep -r "amend_order" src/kalshi_research/execution/` = no matches)
- Developer-only risk (requires direct client instantiation)

**When this becomes P1:**
- If trading CLI is added that exposes order amendment
- If TradeExecutor adds `amend_order` wrapper

---

## Fix Options

### Option A: Full Implementation (Recommended)

```python
async def amend_order(
    self,
    order_id: str,
    ticker: str,
    side: Literal["yes", "no"] | OrderSide,
    action: Literal["buy", "sell"] | OrderAction,
    client_order_id: str,
    updated_client_order_id: str,
    *,
    price: int | None = None,
    price_dollars: str | None = None,
    count: int | None = None,
    dry_run: bool = False,
) -> OrderResponse:
    """
    Amend an existing order's price or quantity.

    Args:
        order_id: The order ID to amend (from order creation response)
        ticker: Market ticker
        side: "yes" or "no"
        action: "buy" or "sell"
        client_order_id: Original client_order_id used when creating the order
        updated_client_order_id: New unique client_order_id for the amended order
        price: New price in cents (1-99), mutually exclusive with price_dollars
        price_dollars: New price in dollars (e.g., "0.5500")
        count: New quantity (optional, can increase up to original order size)
        dry_run: If True, validate and log but do not execute

    Returns:
        OrderResponse with updated order status
    """
```

### Option B: Mark as Not Implemented

```python
async def amend_order(
    self,
    order_id: str,
    price: int | None = None,
    count: int | None = None,
    dry_run: bool = False,
) -> OrderResponse:
    """
    Amend an existing order's price or quantity.

    WARNING: This method is incomplete and will fail against the real API.
    See BUG-065 for details. Use with dry_run=True only until fixed.
    """
    if not dry_run:
        raise NotImplementedError(
            "amend_order() is missing required fields (ticker, side, action, "
            "client_order_id, updated_client_order_id) and will fail against "
            "the real API. See docs/_bugs/BUG-065-amend-order-missing-required-fields.md"
        )
    # ... existing dry_run logic ...
```

---

## Test Plan

- [x] Fix method signature to include all required fields
- [x] Update payload construction to send all required fields
- [x] Update unit test to validate complete payload
- [x] Update integration test flow (respx) to validate complete payload
- [ ] Update docstring with accurate parameter descriptions
- [ ] Consider adding to TradeExecutor with safety wrapper

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/kalshi_research/api/client.py:830-907` | Update `amend_order()` signature and payload |
| `tests/unit/api/test_trading.py:81-93` | Update test to expect complete payload |
| `tests/integration/api/test_trading_integration.py:109-121` | Update integration test |

---

## Related

- **BUG-064:** `create_order()` missing optional safety params (different - those are OPTIONAL)
- **SPEC-034:** TradeExecutor Safety Harness - should include `amend_order` when fixed
- **Vendor docs:** `docs/_vendor-docs/kalshi-api-reference.md:871-916` (Amend Order Full Schema)
