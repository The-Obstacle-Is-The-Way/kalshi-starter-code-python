# Alerts System (Explanation)

The alerts system lets you monitor markets for specific conditions without manually checking Kalshi.

Instead of refreshing the page to see if TRUMP-2024 crossed 60 cents, you set an alert and get notified.

## Alert Types

The monitor evaluates internal `ConditionType` values (stored in `data/alerts.json`). The CLI exposes a safe subset via
`kalshi alerts add`:

| ConditionType | CLI support | Description | Example |
|---|---|---|---|
| `price_above` | ✅ `alerts add price --above` | Midpoint probability goes **above** threshold | `--above 0.60` |
| `price_below` | ✅ `alerts add price --below` | Midpoint probability goes **below** threshold | `--below 0.40` |
| `spread_above` | ✅ `alerts add spread --above` | YES bid/ask spread (cents) goes above threshold | `--above 5` |
| `volume_above` | ✅ `alerts add volume --above` | Total traded volume goes above threshold | `--above 10000` |
| `sentiment_shift` | ✅ `alerts add sentiment --above` | Absolute change in rolling sentiment exceeds threshold | `--above 0.20` |
| `price_crosses` | ⚠️ not exposed | Midpoint crosses a threshold between polling cycles | internal |
| `edge_detected` | ⚠️ not exposed | Absolute midpoint move since last check exceeds threshold | internal |

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
    ticker: str                # Market ticker to monitor
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

Notes:

- The current monitor treats conditions as **one-shot per run**: once a condition triggers, it is removed from the
  in-memory monitor and won’t trigger again until you restart the process.
- Conditions are stored in `data/alerts.json` and are not mutated by the monitor process today.
- Alert statuses exist in code, but there is no CLI workflow yet for acknowledging/clearing triggered alerts.

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

For long-running daemon usage, keep the log size bounded:

```bash
uv run kalshi alerts trim-log          # dry-run default
uv run kalshi alerts trim-log --apply  # execute trimming
```

Note: `trim-log` refuses to run while the daemon is actively writing to the log; stop the daemon first.

## Notifiers

When an alert triggers, notifiers handle the output:

### Console Notifier

Prints to terminal (default):

```text
[ALERT] 2024-01-15 14:32:00 - TRUMP-2024 price above 60c (current: 62c)
```

### File Notifier

Write triggered alerts to a JSONL file (one JSON object per line):

```bash
uv run kalshi alerts monitor --output-file data/alerts_triggered.jsonl
```

### Webhook Notifier

POST alerts to a webhook URL (Slack/Discord-style payload):

```python
class WebhookNotifier:
    def notify(self, alert: Alert) -> None:
        ...
```

## Storage

Alerts are persisted to `data/alerts.json`:

```json
{
  "conditions": [
    {
      "id": "e7a6f5d1-6a33-4d2b-9c6e-0fd8f0b6b2a1",
      "condition_type": "price_above",
      "ticker": "TRUMP-2024",
      "threshold": 0.60,
      "label": "price TRUMP-2024 > 0.6",
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

# Sentiment alerts (only --above supported; requires news/sentiment data in your DB)
uv run kalshi alerts add sentiment TRUMP-2024 --above 0.20
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

# Optional notification sinks
uv run kalshi alerts monitor --output-file data/alerts_triggered.jsonl
uv run kalshi alerts monitor --webhook-url https://example.com/webhook
```

## Condition Evaluation

Each condition type has specific evaluation logic:

Note: In this codebase, `Market.midpoint` and `Market.spread` are computed properties (not raw API fields) derived
from the current YES bid/ask quotes in `src/kalshi_research/api/models/market.py`.

### Price Above/Below

```python
# midpoint is derived from YES bid/ask: (bid + ask) / 2, then scaled to [0, 1]
mid_prob = market.midpoint / 100.0

if condition.condition_type == ConditionType.PRICE_ABOVE:
    triggered = mid_prob > condition.threshold
elif condition.condition_type == ConditionType.PRICE_BELOW:
    triggered = mid_prob < condition.threshold
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
    spread_cents = market.spread
    triggered = spread_cents > condition.threshold
```

### Volume Above

```python
if condition.condition_type == ConditionType.VOLUME_ABOVE:
    triggered = market.volume > condition.threshold
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
- [Usage: Alerts](../getting-started/usage.md#alerts) - CLI commands
