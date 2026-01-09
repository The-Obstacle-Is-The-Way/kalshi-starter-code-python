# BUG-044: WebSocket client silent JSON errors (P2)

**Priority:** P2 (Observability + debugging)
**Status:** 🟢 Fixed (2026-01-08)
**Found:** 2026-01-08
**Checklist Ref:** `code-audit-checklist.md` Section 1 (Silent failures)

---

## Summary

`KalshiWebSocket._handle_message()` swallowed `json.JSONDecodeError` via a bare `pass`, turning malformed/non-JSON
frames into silent no-ops.

---

## Evidence

- `src/kalshi_research/api/websocket/client.py`: `except json.JSONDecodeError: pass`

---

## Root Cause

- An “avoid log spam” impulse led to a silent `pass` instead of a low-noise debug log.

---

## Ironclad Fix

- Log invalid JSON frames at `debug` level with message type/length (no payload).
- Use `logger.exception(...)` for unexpected WebSocket/message parsing errors to preserve tracebacks.
- Add unit tests to lock behavior:
  - invalid JSON triggers a debug log without raising
  - connection checks behave correctly when the socket is closed and auto-reconnect is disabled

---

## Acceptance Criteria

- [x] Invalid JSON frames produce a debug log (not silent), without raising.
- [x] `uv run pre-commit run --all-files` passes.
