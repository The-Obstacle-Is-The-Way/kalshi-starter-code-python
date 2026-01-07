# BUG-006: Missing Alerts System

**Priority:** P1
**Status:** Open
**Discovered:** 2026-01-06
**Spec Reference:** Original CONTEXT FOR CLAUDE, SPEC-005 (new)

---

## Summary

The user explicitly requested an alerts system: "notify me when conditions met". No `alerts.py` or alerting functionality exists anywhere in the codebase.

## User's Original Request

From CONTEXT FOR CLAUDE:
```
├── alerts.py            # NEW - notify me when conditions met
```

And under "Key Research Features":
> "Notify me when conditions met"

## Expected Behavior

A system to:
1. Define alert conditions (price thresholds, spread changes, volume spikes)
2. Monitor markets against those conditions
3. Notify the user when conditions are triggered
4. Support multiple notification channels (console, file, optionally email/webhook)

## Current Behavior

```bash
$ grep -r "alert" src/kalshi_research/
# No results - alerts not implemented
```

No alerting infrastructure exists.

## Root Cause

The alerts module was never implemented. Focus was on data fetching and analysis, but the notification layer was skipped.

## Impact

- **HIGH** - User cannot be notified when research conditions trigger
- This was explicitly requested in the original context
- Makes the platform passive-only (must manually check for opportunities)

## Fix

Implement `src/kalshi_research/alerts/` module:

```python
# alerts/conditions.py
from dataclasses import dataclass
from enum import Enum
from typing import Callable

class ConditionType(Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    SPREAD_ABOVE = "spread_above"
    VOLUME_ABOVE = "volume_above"
    EDGE_DETECTED = "edge_detected"

@dataclass(frozen=True)
class AlertCondition:
    condition_type: ConditionType
    ticker: str
    threshold: float
    label: str

# alerts/monitor.py
class AlertMonitor:
    def __init__(self, conditions: list[AlertCondition]) -> None: ...
    async def check_conditions(self, markets: list[Market]) -> list[Alert]: ...
    def add_condition(self, condition: AlertCondition) -> None: ...
    def remove_condition(self, label: str) -> None: ...

# alerts/notifiers.py
class Notifier(Protocol):
    def notify(self, alert: Alert) -> None: ...

class ConsoleNotifier(Notifier): ...
class FileNotifier(Notifier): ...
class WebhookNotifier(Notifier): ...  # Optional
```

## Acceptance Criteria

- [ ] `alerts/` module exists with conditions, monitor, notifiers
- [ ] Can define alert conditions programmatically
- [ ] AlertMonitor checks markets against conditions
- [ ] ConsoleNotifier prints alerts to terminal with Rich formatting
- [ ] FileNotifier logs alerts to JSON file
- [ ] CLI command `kalshi alerts` to manage/view alerts
- [ ] Tests cover >85% of alerts module
- [ ] mypy --strict passes
