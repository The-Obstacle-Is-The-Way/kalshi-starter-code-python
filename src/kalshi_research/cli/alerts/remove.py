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

    matches: list[tuple[int, dict[str, object]]] = []
    for i, cond in enumerate(conditions):
        cond_id = cond.get("id")
        if isinstance(cond_id, str) and cond_id.startswith(alert_id):
            matches.append((i, cond))

    if not matches:
        console.print(f"[red]Error:[/red] Alert not found: {alert_id}")
        raise typer.Exit(2)

    if len(matches) > 1:
        console.print(f"[red]Error:[/red] Ambiguous alert ID prefix: {alert_id}")
        console.print("[dim]Matches:[/dim]")
        for _, cond in matches:
            console.print(f"  - {cond.get('id', '')} {cond.get('label', '')}")
        console.print("[dim]Provide a longer/full alert id.[/dim]")
        raise typer.Exit(1)

    i, cond = matches[0]
    removed = conditions.pop(i)
    save_alerts(data)
    console.print(f"[green]✓[/green] Alert removed: {removed.get('label', '')}")
