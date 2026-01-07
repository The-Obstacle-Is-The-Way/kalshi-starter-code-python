"""Alert notification channels."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from rich.console import Console
from rich.panel import Panel

if TYPE_CHECKING:
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

        with self._file_path.open("a") as f:
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
                        {
                            "title": "Type",
                            "value": alert.condition.condition_type.value,
                            "short": True,
                        },
                        {
                            "title": "Current Value",
                            "value": str(alert.current_value),
                            "short": True,
                        },
                        {
                            "title": "Threshold",
                            "value": str(alert.condition.threshold),
                            "short": True,
                        },
                    ],
                }
            ],
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                client.post(self._webhook_url, json=payload)
        except httpx.HTTPError:
            pass  # Silently fail for webhooks
