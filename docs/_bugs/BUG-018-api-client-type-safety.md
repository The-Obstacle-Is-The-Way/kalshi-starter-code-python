# BUG-018: API Client Type Safety (Internal)

## Priority
P4 (Low) - Technical Debt

## Description
The internal `_get` method of `KalshiClient` returns `dict[str, Any]`. While public methods convert these to Pydantic models, the internal layer lacks strict typing.

## Location
- `src/kalshi_research/api/client.py`: `_get` method.

## Impact
- **Developer Experience:** Internal maintenance requires care.
- **Reliability:** Public interface is safe, but internal refactoring carries some risk.

## Proposed Fix
1. Eventually define `KalshiResponse[T]` generics.
2. Low priority as public API is typed.
