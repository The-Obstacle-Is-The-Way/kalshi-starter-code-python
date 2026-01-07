# SPEC-005: Alerts & Notifications

**Status:** ✅ Implemented (JSON persistence)
**Priority:** P1 (Explicitly requested in original context)
**Estimated Complexity:** Medium
**Dependencies:** SPEC-002 (API Client), SPEC-003 (Data Layer), SPEC-004 (Analysis)

---

## Implementation References

- `src/kalshi_research/alerts/conditions.py`
- `src/kalshi_research/alerts/monitor.py`
- `src/kalshi_research/alerts/notifiers.py`
- `src/kalshi_research/cli.py` (persists alerts in `data/alerts.json`)

---

## 1. Overview

Implement an alerting system that monitors markets and notifies the user when defined conditions are met. This was explicitly requested in the original context: "notify me when conditions met".

### 1.1 Goals

- Define alert conditions (price thresholds, spread changes, volume spikes, edge detection)
- Monitor markets against those conditions
- Notify the user through multiple channels (console, file, optionally webhooks)
- CLI commands to manage alerts
- Persistent alert storage

### 1.2 Non-Goals

- Real-time streaming (polling is sufficient for research use case)
- Push notifications to mobile devices
- Complex scheduling (cron-based alerting)
- Alert suppression/deduplication (keep simple)

### 1.3 Performance Note

Running `kalshi alerts monitor` in a loop concurrently with `kalshi data collect` will double the API request load for polling markets.
- **Mitigation:** In a production refactor, the alert system should consume events from the data collector.
- **Current Scope:** For this research platform, independent polling is acceptable given Kalshi's generous rate limits for authenticated users, but users should be aware of the overhead.

---

## 2. Core Concepts

### 2.1 Alert Conditions

Types of conditions to monitor:

| Condition Type | Description | Example |
|----------------|-------------|---------|
| `PRICE_ABOVE` | Market probability exceeds threshold | BTC > 70% |
| `PRICE_BELOW` | Market probability drops below threshold | BTC < 30% |
| `PRICE_CROSSES` | Market crosses a threshold in either direction | BTC crosses 50% |
| `SPREAD_ABOVE` | Bid-ask spread exceeds threshold | Spread > 5 cents |
| `VOLUME_ABOVE` | Trading volume exceeds threshold | Volume > 1000 contracts |
| `EDGE_DETECTED` | EdgeDetector finds opportunity | Any thesis edge > 10% |

### 2.2 Alert Lifecycle

```
PENDING → TRIGGERED → ACKNOWLEDGED (optional) → EXPIRED/CLEARED
```

- **PENDING**: Condition not yet met
- **TRIGGERED**: Condition met, notification sent
- **ACKNOWLEDGED**: User has seen the alert (optional workflow)
- **EXPIRED**: Alert reached expiration time without triggering
- **CLEARED**: User manually cleared the alert

### 2.3 Notification Channels

1. **Console**: Rich-formatted terminal output
2. **File**: JSON log file for persistence
3. **Webhook**: HTTP POST to external endpoint (Slack, Discord, etc.)

---

## 3. Technical Specification

### 3.1 Module Structure

```
src/kalshi_research/
├── alerts/
│   ├── __init__.py
│   ├── conditions.py      # AlertCondition definitions
│   ├── monitor.py         # AlertMonitor class
│   ├── notifiers.py       # Notification channels
│   └── storage.py         # Persistent alert storage
```

### 3.2 Conditions Module

```python
# src/kalshi_research/alerts/conditions.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ConditionType(str, Enum):
    """Types of alert conditions."""

    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PRICE_CROSSES = "price_crosses"
    SPREAD_ABOVE = "spread_above"
    VOLUME_ABOVE = "volume_above"
    EDGE_DETECTED = "edge_detected"


class AlertStatus(str, Enum):
    """Alert lifecycle status."""

    PENDING = "pending"
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    EXPIRED = "expired"
    CLEARED = "cleared"


@dataclass
class AlertCondition:
    """
    Defines a condition to monitor.

    Attributes:
        id: Unique identifier for this condition
        condition_type: Type of condition to check
        ticker: Market ticker to monitor (or "*" for all markets)
        threshold: Numeric threshold value
        label: Human-readable description
        expires_at: Optional expiration time
        created_at: When the condition was created
    """

    id: str
    condition_type: ConditionType
    ticker: str
    threshold: float
    label: str
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_expired(self) -> bool:
        """Check if this condition has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at


@dataclass
class Alert:
    """
    A triggered alert.

    Attributes:
        id: Unique alert ID
        condition: The condition that triggered this alert
        triggered_at: When the alert was triggered
        status: Current status
        current_value: The value that triggered the alert
        market_data: Additional market context
    """

    id: str
    condition: AlertCondition
    triggered_at: datetime
    status: AlertStatus
    current_value: float
    market_data: dict[str, Any] = field(default_factory=dict)

    def acknowledge(self) -> None:
        """Mark alert as acknowledged."""
        self.status = AlertStatus.ACKNOWLEDGED

    def clear(self) -> None:
        """Clear the alert."""
        self.status = AlertStatus.CLEARED
```

### 3.3 Monitor Module

```python
# src/kalshi_research/alerts/monitor.py
import uuid
from datetime import datetime, timezone
from typing import Protocol

from kalshi_research.api.models import Market
from kalshi_research.alerts.conditions import (
    Alert,
    AlertCondition,
    AlertStatus,
    ConditionType,
)


class Notifier(Protocol):
    """Protocol for notification channels."""

    def notify(self, alert: Alert) -> None:
        """Send notification for an alert."""
        ...


class AlertMonitor:
    """
    Monitor markets against defined conditions.

    Usage:
        monitor = AlertMonitor()
        monitor.add_notifier(ConsoleNotifier())
        monitor.add_condition(AlertCondition(...))

        # In your polling loop:
        alerts = await monitor.check_conditions(markets)
    """

    def __init__(self) -> None:
        self._conditions: dict[str, AlertCondition] = {}
        self._notifiers: list[Notifier] = []
        self._triggered_alerts: list[Alert] = []

    def add_condition(self, condition: AlertCondition) -> None:
        """Add a condition to monitor."""
        self._conditions[condition.id] = condition

    def remove_condition(self, condition_id: str) -> bool:
        """Remove a condition by ID. Returns True if found."""
        return self._conditions.pop(condition_id, None) is not None

    def add_notifier(self, notifier: Notifier) -> None:
        """Add a notification channel."""
        self._notifiers.append(notifier)

    def list_conditions(self) -> list[AlertCondition]:
        """List all active conditions."""
        return list(self._conditions.values())

    def list_alerts(self) -> list[Alert]:
        """List all triggered alerts."""
        return self._triggered_alerts.copy()

    async def check_conditions(
        self,
        markets: list[Market],
    ) -> list[Alert]:
        """
        Check all conditions against current market data.

        Args:
            markets: List of current market data

        Returns:
            List of newly triggered alerts
        """
        new_alerts: list[Alert] = []
        market_lookup = {m.ticker: m for m in markets}

        for condition in list(self._conditions.values()):
            # Skip expired conditions
            if condition.is_expired():
                del self._conditions[condition.id]
                continue

            # Check if condition matches
            alert = self._check_condition(condition, market_lookup)
            if alert:
                new_alerts.append(alert)
                self._triggered_alerts.append(alert)

                # Notify all channels
                for notifier in self._notifiers:
                    notifier.notify(alert)

                # Remove one-shot conditions after triggering
                del self._conditions[condition.id]

        return new_alerts

    def _check_condition(
        self,
        condition: AlertCondition,
        markets: dict[str, Market],
    ) -> Alert | None:
        """Check a single condition against market data."""
        market = markets.get(condition.ticker)
        if market is None:
            return None

        triggered = False
        current_value = 0.0

        match condition.condition_type:
            case ConditionType.PRICE_ABOVE:
                current_value = market.yes_price / 100.0
                triggered = current_value > condition.threshold

            case ConditionType.PRICE_BELOW:
                current_value = market.yes_price / 100.0
                triggered = current_value < condition.threshold

            case ConditionType.SPREAD_ABOVE:
                spread = market.yes_ask - market.yes_bid
                current_value = float(spread)
                triggered = current_value > condition.threshold

            case ConditionType.VOLUME_ABOVE:
                current_value = float(market.volume)
                triggered = current_value > condition.threshold

        if triggered:
            return Alert(
                id=str(uuid.uuid4()),
                condition=condition,
                triggered_at=datetime.now(timezone.utc),
                status=AlertStatus.TRIGGERED,
                current_value=current_value,
                market_data={
                    "ticker": market.ticker,
                    "title": market.title,
                    "yes_price": market.yes_price,
                    "volume": market.volume,
                },
            )

        return None
```

### 3.4 Notifiers Module

```python
# src/kalshi_research/alerts/notifiers.py
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from rich.console import Console
from rich.panel import Panel

from kalshi_research.alerts.conditions import Alert


class ConsoleNotifier:
    """Rich console notification output."""

    def __init__(self) -> None:
        self._console = Console()

    def notify(self, alert: Alert) -> None:
        """Print alert to console with Rich formatting."""
        content = (
            f"[bold]{alert.condition.label}[/bold]\n\n"
            f"Ticker: {alert.condition.ticker}\n"
            f"Type: {alert.condition.condition_type.value}\n"
            f"Threshold: {alert.condition.threshold}\n"
            f"Current Value: {alert.current_value}\n"
            f"Triggered: {alert.triggered_at.isoformat()}"
        )

        self._console.print(
            Panel(
                content,
                title="[red]ALERT TRIGGERED[/red]",
                border_style="red",
            )
        )


class FileNotifier:
    """JSON file logging for alerts."""

    def __init__(self, file_path: Path | str) -> None:
        self._file_path = Path(file_path)
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    def notify(self, alert: Alert) -> None:
        """Append alert to JSON lines file."""
        record: dict[str, Any] = {
            "id": alert.id,
            "condition_id": alert.condition.id,
            "condition_type": alert.condition.condition_type.value,
            "ticker": alert.condition.ticker,
            "label": alert.condition.label,
            "threshold": alert.condition.threshold,
            "current_value": alert.current_value,
            "triggered_at": alert.triggered_at.isoformat(),
            "market_data": alert.market_data,
        }

        with open(self._file_path, "a") as f:
            f.write(json.dumps(record) + "\n")


class WebhookNotifier:
    """HTTP webhook notification (for Slack, Discord, etc.)."""

    def __init__(self, webhook_url: str, timeout: float = 10.0) -> None:
        self._webhook_url = webhook_url
        self._timeout = timeout

    def notify(self, alert: Alert) -> None:
        """POST alert to webhook endpoint."""
        payload = {
            "text": f"Alert: {alert.condition.label}",
            "attachments": [
                {
                    "color": "danger",
                    "fields": [
                        {"title": "Ticker", "value": alert.condition.ticker, "short": True},
                        {"title": "Type", "value": alert.condition.condition_type.value, "short": True},
                        {"title": "Current Value", "value": str(alert.current_value), "short": True},
                        {"title": "Threshold", "value": str(alert.condition.threshold), "short": True},
                    ],
                }
            ],
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                client.post(self._webhook_url, json=payload)
        except httpx.HTTPError:
            pass  # Silently fail for webhooks
```

### 3.5 CLI Integration

```python
# Add to cli.py

alerts_app = typer.Typer(help="Alert management commands.")
app.add_typer(alerts_app, name="alerts")


@alerts_app.command("add")
def add_alert(
    ticker: Annotated[str, typer.Argument(help="Market ticker to monitor")],
    condition: Annotated[str, typer.Option("--condition", "-c", help="Condition type: price_above, price_below, spread_above, volume_above")],
    threshold: Annotated[float, typer.Option("--threshold", "-t", help="Threshold value")],
    label: Annotated[str, typer.Option("--label", "-l", help="Alert label")] = "",
) -> None:
    """Add a new alert condition."""
    ...


@alerts_app.command("list")
def list_alerts() -> None:
    """List all active alert conditions."""
    ...


@alerts_app.command("remove")
def remove_alert(
    alert_id: Annotated[str, typer.Argument(help="Alert ID to remove")],
) -> None:
    """Remove an alert condition."""
    ...


@alerts_app.command("monitor")
def monitor_alerts(
    interval: Annotated[int, typer.Option("--interval", "-i", help="Check interval in seconds")] = 60,
) -> None:
    """Start monitoring for alerts (runs continuously)."""
    ...
```

---

## 4. Implementation Tasks

### 4.1 Phase 1: Core Module

- [ ] Create `alerts/` package structure
- [ ] Implement `AlertCondition` and `Alert` dataclasses
- [ ] Implement `AlertMonitor` with condition checking
- [ ] Write unit tests for condition checking logic

### 4.2 Phase 2: Notifiers

- [ ] Implement `ConsoleNotifier` with Rich formatting
- [ ] Implement `FileNotifier` with JSON lines
- [ ] Implement `WebhookNotifier` for external integrations
- [ ] Write tests for notifiers

### 4.3 Phase 3: CLI Integration

- [ ] Add `alerts add` command
- [ ] Add `alerts list` command
- [ ] Add `alerts remove` command
- [ ] Add `alerts monitor` command with polling loop
- [ ] Write CLI integration tests

### 4.4 Phase 4: Persistence

- [ ] Add SQLite storage for alert conditions
- [ ] Load/save conditions on startup/shutdown
- [ ] Alert history table for triggered alerts

---

## 5. Acceptance Criteria

1. **Conditions**: All 6 condition types work correctly
2. **Monitoring**: Check interval configurable, handles API errors gracefully
3. **Notifications**: Console shows Rich-formatted alerts, file logs JSON
4. **CLI**: All alert commands work (`add`, `list`, `remove`, `monitor`)
5. **Persistence**: Conditions survive restart
6. **Tests**: >85% coverage on alerts module

---

## 6. Usage Examples

```python
# Programmatic usage
from kalshi_research.alerts import AlertMonitor, AlertCondition, ConditionType
from kalshi_research.alerts.notifiers import ConsoleNotifier, FileNotifier

# Set up monitor
monitor = AlertMonitor()
monitor.add_notifier(ConsoleNotifier())
monitor.add_notifier(FileNotifier("data/alerts.jsonl"))

# Add conditions
monitor.add_condition(AlertCondition(
    id="btc-high",
    condition_type=ConditionType.PRICE_ABOVE,
    ticker="KXBTC-25JAN-T100000",
    threshold=0.75,
    label="BTC >$100k hitting 75%",
))

monitor.add_condition(AlertCondition(
    id="wide-spread",
    condition_type=ConditionType.SPREAD_ABOVE,
    ticker="INXU-25JAN-B200",
    threshold=5.0,
    label="S&P spread > 5 cents",
))

# Check conditions (in your polling loop)
async with KalshiPublicClient() as client:
    markets = [m async for m in client.get_all_markets(status="open")]
    alerts = await monitor.check_conditions(markets)
    for alert in alerts:
        print(f"Triggered: {alert.condition.label}")
```

```bash
# CLI usage
kalshi alerts add KXBTC-25JAN-T100000 -c price_above -t 0.75 -l "BTC bullish"
kalshi alerts list
kalshi alerts monitor --interval 60
kalshi alerts remove btc-high
```

---

## 7. Future Considerations

- Email notifications (SMTP)
- SMS notifications (Twilio)
- Alert grouping and rate limiting
- Complex compound conditions (AND/OR)
- Machine learning-based anomaly alerts
- Integration with trading execution (alert → auto-place order)
