# BUG-018: API Client Lacks Strict Typing

## Priority
P2 (Medium) - Quality/Reliability

## Description
The core `KalshiClient` and `KalshiPublicClient` rely heavily on `Any` and `dict[str, Any]` for return types and internal method signatures. This completely bypasses static type checking (mypy) and makes the client brittle.

The `_get` method returns `dict[str, Any]`, meaning all downstream consumers must manually cast or assume types, leading to potential `KeyError` or `TypeError` at runtime that should have been caught at compile time.

## Location
- `src/kalshi_research/api/client.py`: Lines 59, 84, and throughout method signatures.

## Impact
- **Developer Experience:** No IDE autocompletion for API responses.
- **Reliability:** Refactoring is dangerous as the type system cannot verify changes.
- **Bugs:** "Stringly typed" code is prone to typos in dictionary keys.

## Proposed Fix
1. Define specific Pydantic models for all API response wrappers (e.g., `KalshiResponse[T]`).
2. Update `_get` and other HTTP methods to use generics `T` and return typed objects.
3. Remove `Any` from public method signatures and replace with concrete Pydantic models.
