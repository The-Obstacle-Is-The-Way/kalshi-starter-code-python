# BUG-045: Legacy WebSocket Client Uses print() Instead of Logger (P3)

**Priority:** P3 (Code quality / Observability)
**Status:** Open
**Found:** 2026-01-08
**Checklist Ref:** `CODE_AUDIT_CHECKLIST.md` Section 1 (Logging anti-patterns)

---

## Summary

The legacy `KalshiWebSocketClient` class in `src/kalshi_research/clients.py` uses `print()` statements instead of proper logging. This breaks observability patterns and produces unstructured output that cannot be filtered, routed, or integrated with logging infrastructure.

---

## Evidence

```python
# src/kalshi_research/clients.py

# Line 215
async def on_open(self) -> None:
    """Callback when WebSocket connection is opened."""
    print("WebSocket connection opened.")  # BUG: Should be logger.info()

# Line 246
async def on_message(self, message: str | bytes) -> None:
    """Callback for handling incoming messages."""
    print("Received message:", message)  # BUG: Should be logger.debug()

# Line 250
async def on_error(self, error: Exception) -> None:
    """Callback for handling errors."""
    print("WebSocket error:", error)  # BUG: Should be logger.error() or logger.exception()

# Line 254
async def on_close(self, close_status_code: int | None, close_msg: str | None) -> None:
    """Callback when WebSocket connection is closed."""
    print(f"WebSocket connection closed with code: {close_status_code}, message: {close_msg}")  # BUG: Should be logger.info()
```

---

## Root Cause

This appears to be example/starter code that was never updated to use proper logging patterns. The newer `KalshiWebSocket` class in `api/websocket/client.py` correctly uses structured logging.

---

## Impact

- **Observability:** Cannot filter WebSocket logs separately from other output
- **Production:** print() to stdout may be lost or interleaved with other output
- **Testing:** Harder to verify correct logging behavior in tests
- **Debugging:** No timestamps, log levels, or context in output

---

## Ironclad Fix

Replace all `print()` calls with appropriate logger calls:

```python
import logging

logger = logging.getLogger(__name__)

async def on_open(self) -> None:
    logger.info("WebSocket connection opened")

async def on_message(self, message: str | bytes) -> None:
    logger.debug("Received WebSocket message", extra={"length": len(message)})

async def on_error(self, error: Exception) -> None:
    logger.exception("WebSocket error: %s", error)

async def on_close(self, close_status_code: int | None, close_msg: str | None) -> None:
    logger.info("WebSocket connection closed", extra={"code": close_status_code, "message": close_msg})
```

---

## Acceptance Criteria

- [ ] All `print()` statements in `clients.py` replaced with `logger.*()` calls
- [ ] Logger is imported at module level: `logger = logging.getLogger(__name__)`
- [ ] Log levels are appropriate: `info` for connection events, `debug` for messages, `exception` for errors
- [ ] `uv run pre-commit run --all-files` passes

---

## Notes

This is a legacy client class. Consider whether this class should be deprecated in favor of the newer `KalshiWebSocket` class in `api/websocket/client.py` which already follows proper patterns.
