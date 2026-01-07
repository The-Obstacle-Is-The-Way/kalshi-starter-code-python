# BUG-021: Broad Exception Handling Patterns

## Priority
P2 (Medium) - Debuggability

## Description
Several modules use broad `except Exception:` blocks that catch all errors and either just log them or pass. This is an anti-pattern that can mask critical failures (like `KeyboardInterrupt` or `MemoryError`) and make debugging extremely difficult.

## Location
- `src/kalshi_research/research/notebook_utils.py`: Line 69
- `src/kalshi_research/clients.py`: Line 234 (WebSocket message loop)

## Impact
- **Silent Failures:** The application might continue running in a corrupted state after a serious error.
- **Zombie Processes:** `KeyboardInterrupt` might be caught, preventing the user from stopping the process.

## Proposed Fix
1. Change `except Exception` to catch specific exceptions (e.g., `ConnectionError`, `ValueError`).
2. If a catch-all is needed for a top-level loop, ensure it explicitly re-raises `SystemExit` and `KeyboardInterrupt`.
3. Ensure all caught exceptions are logged with full stack traces (`logger.exception`).
