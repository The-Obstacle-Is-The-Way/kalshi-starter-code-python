"""Add alert command."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

import typer

from kalshi_research.cli.alerts._helpers import load_alerts, save_alerts
from kalshi_research.cli.utils import console


def alerts_add(
    alert_type: Annotated[str, typer.Argument(help="Alert type: price, volume, spread, sentiment")],
    ticker: Annotated[str, typer.Argument(help="Market ticker to monitor")],
    above: Annotated[
        float | None, typer.Option("--above", help="Trigger when above threshold")
    ] = None,
    below: Annotated[
        float | None, typer.Option("--below", help="Trigger when below threshold")
    ] = None,
) -> None:
    """Add a new alert condition."""
    from kalshi_research.alerts import ConditionType

    alert_type = alert_type.strip().lower()

    if above is not None and below is not None:
        console.print("[red]Error:[/red] Specify only one of --above or --below")
        raise typer.Exit(1)

    if above is None and below is None:
        console.print("[red]Error:[/red] Must specify either --above or --below")
        raise typer.Exit(1)

    # Validate: volume/spread/sentiment only support --above (no BELOW condition types exist)
    if alert_type in ("volume", "spread", "sentiment") and below is not None:
        console.print(f"[red]Error:[/red] {alert_type} alerts only support --above threshold")
        raise typer.Exit(1)

    # Map alert type to condition type
    type_map: dict[str, ConditionType] = {
        "price": ConditionType.PRICE_ABOVE if above is not None else ConditionType.PRICE_BELOW,
        "volume": ConditionType.VOLUME_ABOVE,
        "spread": ConditionType.SPREAD_ABOVE,
        "sentiment": ConditionType.SENTIMENT_SHIFT,
    }

    if alert_type not in type_map:
        console.print(f"[red]Error:[/red] Unknown alert type: {alert_type}")
        raise typer.Exit(1)

    condition_type = type_map[alert_type]
    threshold = above if above is not None else below

    # Create alert condition
    alert_id = str(uuid.uuid4())
    comparison = ">" if above is not None else "<"
    if condition_type == ConditionType.SENTIMENT_SHIFT:
        comparison = "|Δ| ≥"
    condition = {
        "id": alert_id,
        "condition_type": condition_type.value,
        "ticker": ticker,
        "threshold": threshold,
        "label": f"{alert_type} {ticker} {comparison} {threshold}",
        "created_at": datetime.now(UTC).isoformat(),
    }

    # Save to storage
    data = load_alerts()
    data.setdefault("conditions", []).append(condition)
    save_alerts(data)

    console.print(f"[green]✓[/green] Alert added: {condition['label']}")
    console.print(f"[dim]ID: {alert_id[:8]}[/dim]")
