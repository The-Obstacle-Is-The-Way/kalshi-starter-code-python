# BUG-088: CLI Tests Became Order-Dependent After `client_factory` Migration

**Priority:** P1 (High - blocks reliable quality gates)
**Status:** ✅ Fixed (2026-01-20)
**Found:** 2026-01-20
**Location:** `tests/unit/cli/test_news.py` (and other CLI tests that patched `KalshiPublicClient` directly)

---

## Summary

After migrating CLI modules to use `kalshi_research.cli.client_factory` (DEBT-046), some CLI tests became
**order-dependent** due to mock patch leakage:

- `test_news_track_ticker_not_found_exits` passed in isolation
- but failed when run after `test_news_track_event_with_custom_queries`

This broke deterministic CI/loop operation (Ralph Wiggum relies on stable `uv run pytest`).

---

## Evidence (Before Fix)

```bash
uv run pytest tests/unit/cli/test_news.py -k "track_event_with_custom_queries or track_ticker_not_found_exits" -vv
```

Failure:

```text
AttributeError: 'coroutine' object has no attribute 'strip'
```

---

## Root Cause

CLI code now calls the factory:

- `kalshi_research.cli.client_factory.public_client()`

But some tests were still patching the underlying constructor:

- `patch("kalshi_research.api.KalshiPublicClient", ...)`

`client_factory.py` imports `KalshiPublicClient` at module import time:

```python
from kalshi_research.api import KalshiPublicClient
```

If `client_factory` is first imported while the constructor is patched, the patched object can be captured
inside `client_factory` and persist beyond the patch context, causing later tests to unexpectedly use the wrong
mock client.

---

## Fix Implemented

- Updated CLI tests to patch the factory functions instead of client constructors:
  - `kalshi_research.cli.client_factory.public_client`
  - `kalshi_research.cli.client_factory.authed_client`

Files updated:
- `tests/unit/cli/test_news.py`
- `tests/unit/cli/test_data.py`
- `tests/unit/cli/test_alerts.py`
- `tests/unit/cli/test_research.py`
- `tests/integration/cli/test_cli_commands.py`

This aligns with DEBT-046’s intent: patch the boundary we own (the factory), not the implementation detail (client
constructor).

---

## Verification

- `uv run pytest tests/unit/cli -q`
- `uv run pytest`

---

## Related

- DEBT-046: `docs/_debt/DEBT-046-dependency-inversion-client-factory.md`
