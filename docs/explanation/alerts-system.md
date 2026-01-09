# Alerts System (Explanation)

The alerts system lets you monitor markets for specific conditions without manually checking Kalshi.

Instead of refreshing the page to see if TRUMP-2024 crossed 60 cents, you set an alert and get notified.

## Alert Types

The system supports several condition types:

| Type | Description | Example |
|------|-------------|---------|
| `price_above` | YES price exceeds threshold | Alert when TRUMP > 60c |
| `price_below` | YES price drops below threshold | Alert when TRUMP < 40c |
| `price_crosses` | Price crosses threshold (either direction) | Alert when TRUMP crosses 50c |
| `spread_above` | Bid-ask spread exceeds threshold | Alert when spread > 5c |
| `volume_above` | 24h volume exceeds threshold | Alert when volume > 10,000 |
| `edge_detected` | Market matches your thesis edge criteria | Custom edge alerts |

## Architecture

```text
AlertCondition (data/alerts.json)
        │
        ▼
  AlertMonitor (polling loop)
        │
    ┌───┴───┐
    ▼       ▼
Kalshi API  Check conditions
    │              │
    └──────┬───────┘
           ▼
      Alert triggered?
           │
    ┌──────┴──────┐
    ▼             ▼
   Yes           No
    │             │
    ▼             │
Notifiers        (continue)
(console, file, webhook)
```

## Data Model

### AlertCondition

Defines what to watch for:

```python
@dataclass
class AlertCondition:
    id: str                    # Unique identifier
    condition_type: ConditionType
    ticker: str                # Market ticker (or "*" for all)
    threshold: float           # Numeric threshold
    label: str                 # Human-readable description
    expires_at: datetime | None  # Optional expiration
    created_at: datetime
```

### Alert

A triggered alert:

```python
@dataclass
class Alert:
    id: str
    condition: AlertCondition  # The condition that triggered
    triggered_at: datetime
    status: AlertStatus        # pending, triggered, acknowledged, cleared
    current_value: float       # The value that triggered it
    market_data: dict          # Additional context
```

## Alert Lifecycle

```text
PENDING ──► TRIGGERED ──► ACKNOWLEDGED ──► CLEARED
                │
                └──► EXPIRED (if expires_at passed)
```

- **Pending**: Condition is being monitored
- **Triggered**: Condition was met, alert fired
- **Acknowledged**: You saw it (optional)
- **Cleared**: Alert dismissed
- **Expired**: Condition's expiration time passed

## Monitoring Modes

### One-shot

Check once and exit:

```bash
uv run kalshi alerts monitor --once
```

### Polling Loop

Check repeatedly at an interval:

```bash
uv run kalshi alerts monitor --interval 60  # Check every 60 seconds
```

### Daemon Mode

Run in background (detached process):

```bash
uv run kalshi alerts monitor --daemon --interval 60
```

Daemon mode spawns a background process that continues running after you close the terminal.

## Notifiers

When an alert triggers, notifiers handle the output:

### Console Notifier

Prints to terminal (default):

```text
[ALERT] 2024-01-15 14:32:00 - TRUMP-2024 price above 60c (current: 62c)
```

### File Notifier

Appends to a log file:

```bash
# Configured via CLI or code
```

### Webhook Notifier

POSTs to a URL (for Slack, Discord, etc.):

```python
class WebhookNotifier:
    def notify(self, alert: Alert) -> None:
        requests.post(self.url, json={
            "text": f"Alert: {alert.condition.label}",
            "value": alert.current_value,
        })
```

## Storage

Alerts are persisted to `data/alerts.json`:

```json
{
  "conditions": [
    {
      "id": "abc123",
      "condition_type": "price_above",
      "ticker": "TRUMP-2024",
      "threshold": 0.60,
      "label": "TRUMP above 60c",
      "expires_at": null,
      "created_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

## CLI Usage

### Add Alerts

```bash
# Price alerts
uv run kalshi alerts add price TRUMP-2024 --above 0.60
uv run kalshi alerts add price TRUMP-2024 --below 0.40

# Volume alerts (only --above supported)
uv run kalshi alerts add volume TRUMP-2024 --above 10000

# Spread alerts (only --above supported)
uv run kalshi alerts add spread TRUMP-2024 --above 5
```

### List Alerts

```bash
uv run kalshi alerts list
```

### Remove Alerts

```bash
uv run kalshi alerts remove <ALERT_ID_PREFIX>
```

### Monitor

```bash
# One-shot check
uv run kalshi alerts monitor --once

# Continuous monitoring
uv run kalshi alerts monitor --interval 60

# Background daemon
uv run kalshi alerts monitor --daemon --interval 60
```

## Condition Evaluation

Each condition type has specific evaluation logic:

### Price Above/Below

```python
if condition.condition_type == ConditionType.PRICE_ABOVE:
    triggered = market.yes_price >= condition.threshold
elif condition.condition_type == ConditionType.PRICE_BELOW:
    triggered = market.yes_price <= condition.threshold
```

### Price Crosses

Triggers on first cross in either direction:

```python
if condition.condition_type == ConditionType.PRICE_CROSSES:
    # Requires previous state tracking
    crossed = (prev < threshold <= current) or (prev > threshold >= current)
```

### Spread Above

```python
if condition.condition_type == ConditionType.SPREAD_ABOVE:
    spread = market.yes_ask - market.yes_bid
    triggered = spread >= condition.threshold
```

### Volume Above

```python
if condition.condition_type == ConditionType.VOLUME_ABOVE:
    triggered = market.volume_24h >= condition.threshold
```

## Use Cases

1. **Entry signals**: Alert when a market hits your target entry price
2. **Exit signals**: Alert when a position reaches your take-profit or stop-loss
3. **Liquidity monitoring**: Alert when spread tightens (good time to trade)
4. **Volume spikes**: Alert on unusual activity (might indicate news)
5. **Thesis tracking**: Alert when markets related to your thesis move significantly

## Key Code

- Conditions: `src/kalshi_research/alerts/conditions.py`
- Monitor: `src/kalshi_research/alerts/monitor.py`
- Notifiers: `src/kalshi_research/alerts/notifiers.py`
- CLI: `src/kalshi_research/cli/alerts.py`
- Storage path: `src/kalshi_research/paths.py` (`DEFAULT_ALERTS_PATH`)

## See Also

- [Scanner](scanner.md) - Find opportunities proactively
- [Usage: Alerts](../how-to/usage.md#alerts) - CLI commands
