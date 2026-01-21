"""Remove alert command."""

from typing import Annotated

import typer

from kalshi_research.cli.alerts._helpers import load_alerts, save_alerts
from kalshi_research.cli.utils import console


def alerts_remove(
    alert_id: Annotated[str, typer.Argument(help="Alert ID prefix to remove")],
) -> None:
    """Remove an alert by ID prefix."""
    data = load_alerts()
    conditions = data.get("conditions", [])

    # Find and remove
    for i, cond in enumerate(conditions):
        if cond["id"].startswith(alert_id):
            removed = conditions.pop(i)
            save_alerts(data)
            console.print(f"[green]✓[/green] Alert removed: {removed['label']}")
            return

    console.print(f"[red]Error:[/red] Alert not found: {alert_id}")
    raise typer.Exit(2)
