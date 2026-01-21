"""Typer CLI commands for creating and monitoring alerts.

This package provides alert commands for the Kalshi CLI:
- list: List all active alerts
- add: Add a new alert condition
- remove: Remove an alert by ID prefix
- monitor: Start monitoring alerts (runs in foreground or background daemon)
- trim-log: Trim the alerts monitor log to keep disk usage bounded
"""

import typer

from kalshi_research.cli.alerts.add_cmd import alerts_add
from kalshi_research.cli.alerts.list_cmd import alerts_list
from kalshi_research.cli.alerts.monitor import alerts_monitor
from kalshi_research.cli.alerts.remove import alerts_remove
from kalshi_research.cli.alerts.trim_log import alerts_trim_log

# Create main app and register commands
app = typer.Typer(help="Alert management commands.")

app.command("list")(alerts_list)
app.command("add")(alerts_add)
app.command("remove")(alerts_remove)
app.command("monitor")(alerts_monitor)
app.command("trim-log")(alerts_trim_log)

__all__ = [
    "alerts_add",
    "alerts_list",
    "alerts_monitor",
    "alerts_remove",
    "alerts_trim_log",
    "app",
]
