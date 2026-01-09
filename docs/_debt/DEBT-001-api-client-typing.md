# DEBT-001: Inconsistent API Client Return Types

## Overview
The `KalshiClient` exhibits a "split-brain" typing strategy. Market data methods return strict Pydantic models, while Portfolio methods return raw `dict` or `list[dict]`.

## Severity: Medium (Developer Experience / Safety)
- **Impact**: Callers must guess dictionary keys (e.g., `pos["position"]` vs `pos["count"]`). This defeats the purpose of using strict typing and Pydantic throughout the rest of the codebase.
- **Risk**: Runtime `KeyError` if the API schema changes or if the developer creates a typo.

## Vendor Verification (SSOT)
- **Source**: `docs/_vendor-docs/kalshi-api-reference.md` (Section: Portfolio)
- **Citation**: Lists specific fields for endpoints (e.g., `balance`, `portfolio_value` for `/portfolio/balance`).
- **Confirmation**: The API returns structured, predictable JSON objects. The use of raw `dict` in the client is an implementation choice (debt), not an API limitation.

## Affected Methods
**File:** `src/kalshi_research/api/client.py`

| Method | Current Return Type | Expected Return Type |
|--------|---------------------|----------------------|
| `get_balance` | `dict[str, Any]` | `PortfolioBalance` model |
| `get_positions` | `list[dict[str, Any]]` | `list[PortfolioPosition]` |
| `get_orders` | `list[dict[str, Any]]` | `list[Order]` |
| `get_fills` | `dict[str, Any]` | `FillPage` / `list[Fill]` |
| `cancel_order` | `dict[str, Any]` | `OrderResponse` (or status model) |

## Plan
1. Create Pydantic models in `src/kalshi_research/api/models/portfolio.py`.
2. Update `KalshiClient` methods to validate and return these models.
3. Update tests in `tests/unit/api/test_client.py` to assert model types.
