# BUG-041: WebSocket connect uses wrong headers kwarg for `websockets` v15 (P0)

**Priority:** P0 (Runtime failure: authenticated WS cannot connect)
**Status:** 🟢 Fixed (2026-01-08)
**Found:** 2026-01-08
**Area:** `src/kalshi_research/api/websocket/client.py`

---

## Summary

The new WebSocket client calls `websockets.connect(..., extra_headers=...)`, but this repo depends on
`websockets>=15`, where the keyword argument is `additional_headers`. This causes an immediate runtime error or
silently drops auth headers, preventing authenticated/private channels from working.

---

## Evidence / Reproduction

- Repo uses `websockets 15.x` (`uv run python -c "import websockets; print(websockets.__version__)"`).
- In `websockets 15.x`, `websockets.connect` accepts `additional_headers`, not `extra_headers`:

```bash
uv run python - <<'PY'
import inspect, websockets
print(websockets.__version__)
print(inspect.signature(websockets.connect))
PY
```

- Code currently does:
  - `src/kalshi_research/api/websocket/client.py`: `websockets.connect(self._url, extra_headers=headers)`
- Unit test currently asserts `extra_headers`, which masks the issue by patching `websockets.connect` instead of
  exercising the real signature:
  - `tests/unit/api/websocket/test_websocket.py`

---

## Root Cause

Mismatch between the code and the installed `websockets` API for v15+.

---

## Ironclad Fix

- Update `KalshiWebSocket.connect()` to call `websockets.connect(..., additional_headers=headers)`.
  - File: `src/kalshi_research/api/websocket/client.py`
- Update unit tests to assert `additional_headers`.
  - File: `tests/unit/api/websocket/test_websocket.py`

---

## Acceptance Criteria

- [x] `KalshiWebSocket.connect()` passes auth headers on `websockets 15.x` without raising.
- [x] Unit tests assert `additional_headers` (not `extra_headers`) and pass.
- [x] `uv run pre-commit run --all-files` passes.
- [x] `uv run pytest -m "not integration and not slow"` passes.
