# BUG-045: Legacy Starter Code Compatibility Layer Issues (P3)

**Priority:** P3 (Code quality / Technical debt)
**Status:** ✅ Fixed (Removed)
**Found:** 2026-01-08
**Fixed:** 2026-01-08
**Checklist Ref:** `CODE_AUDIT_CHECKLIST.md` Section 1 (Logging anti-patterns, Dead code)

---

## Summary

The `src/kalshi_research/clients.py` file was a **legacy starter code compatibility layer** that:

1. Used `print()` statements instead of proper logging (4 instances)
2. Was **NOT used anywhere** in the main application code (only re-exported for backwards compatibility)
3. Duplicated functionality that exists in the modern async API clients
4. Had extensive tests validating code that nothing used

---

## Resolution: Option A (Remove Legacy Layer)

The legacy code was surgically removed:

- [x] Removed `src/kalshi_research/clients.py` (255 lines)
- [x] Updated `src/kalshi_research/__init__.py` to remove legacy exports
- [x] Removed `tests/unit/test_clients.py` (621 lines)
- [x] Removed `requests` dependency from `pyproject.toml`
- [x] Removed `types-requests` dev dependency
- [x] `uv run pre-commit run --all-files` passes
- [x] All 381 unit tests pass

---

## Origin Analysis

Web search confirmed the legacy code originated from the official Kalshi starter repository:
- **Source:** [Kalshi/kalshi-starter-code-python](https://github.com/Kalshi/kalshi-starter-code-python)
- **File:** `clients.py` with `KalshiHttpClient`, `KalshiWebSocketClient`, `KalshiBaseClient`
- The `print()` statements in WebSocket callbacks are from the official example code

---

## Modern API (Now Sole Implementation)

| Class | Location | Features |
|-------|----------|----------|
| `KalshiPublicClient` | `api/client.py` | async httpx, tenacity retries, proper error handling |
| `KalshiClient` | `api/client.py` | Extends public, adds auth, rate limiting |
| `KalshiWebSocket` | `api/websocket/client.py` | structlog, auto-reconnect, typed messages |

---

## Impact

- **Lines removed:** 876 (255 in clients.py + 621 in test_clients.py)
- **Dependencies removed:** `requests`, `types-requests`
- **Breaking change:** Users importing legacy classes from `kalshi_research` will get ImportError
- **Migration path:** Use modern clients from `kalshi_research.api`

---

## Related

- **BUG-024** (Fixed): Legacy client missing timeouts - now moot (code removed)
- **BUG-044** (Fixed): Modern WebSocket client silent JSON errors - fixed with logging
