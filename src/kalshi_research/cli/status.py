"""Typer CLI commands for exchange status and operational info."""

from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.table import Table

from kalshi_research.cli.utils import console, run_async

app = typer.Typer(help="Exchange status and operational information.")

_WEEK_DAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def _render_exchange_status_table(status: dict[str, object]) -> None:
    table = Table(title="Exchange Status")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    exchange_active = status.get("exchange_active")
    trading_active = status.get("trading_active")
    table.add_row("exchange_active", str(exchange_active))
    table.add_row("trading_active", str(trading_active))

    extra_keys = [k for k in status if k not in {"exchange_active", "trading_active"}]
    for key in sorted(extra_keys):
        table.add_row(key, str(status[key]))

    console.print(table)


def _render_exchange_schedule(payload: dict[str, object]) -> None:
    schedule = payload.get("schedule")
    if not isinstance(schedule, dict):
        console.print("[red]Error:[/red] Unexpected schedule response shape.")
        raise typer.Exit(1)

    _render_standard_hours(schedule.get("standard_hours"))
    _render_maintenance_windows(schedule.get("maintenance_windows"))


def _render_standard_hours(standard_hours: object) -> None:
    if not isinstance(standard_hours, list) or not standard_hours:
        return

    first = standard_hours[0]
    if not isinstance(first, dict):
        return

    table = Table(title="Standard Hours (ET)")
    table.add_column("Day", style="cyan", no_wrap=True)
    table.add_column("Sessions", style="green")

    for day in _WEEK_DAYS:
        sessions = first.get(day)
        if not isinstance(sessions, list):
            continue
        parts: list[str] = []
        for session in sessions:
            if not isinstance(session, dict):
                continue
            open_time = session.get("open_time")
            close_time = session.get("close_time")
            if isinstance(open_time, str) and isinstance(close_time, str):
                parts.append(f"{open_time}-{close_time}")
        table.add_row(day, ", ".join(parts))

    console.print(table)


def _render_maintenance_windows(maintenance_windows: object) -> None:
    if not isinstance(maintenance_windows, list) or not maintenance_windows:
        return

    table = Table(title="Maintenance Windows")
    table.add_column("Start", style="cyan", no_wrap=True)
    table.add_column("End", style="cyan", no_wrap=True)
    for window in maintenance_windows[:50]:
        if not isinstance(window, dict):
            continue
        start = window.get("start_datetime")
        end = window.get("end_datetime")
        table.add_row(str(start or ""), str(end or ""))

    console.print(table)


@app.callback(invoke_without_command=True)
def status(
    ctx: typer.Context,
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """Show Kalshi exchange operational status."""
    from kalshi_research.api import KalshiPublicClient

    if ctx.invoked_subcommand is not None:
        return

    async def _fetch() -> dict[str, object]:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                raw = await client.get_exchange_status()
            except KalshiAPIError as e:
                console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
                raise typer.Exit(1) from None
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        if not isinstance(raw, dict):
            console.print("[red]Error:[/red] Unexpected exchange status response type")
            raise typer.Exit(1) from None
        return raw

    payload = run_async(_fetch())

    if output_json:
        typer.echo(json.dumps(payload, indent=2, default=str))
        return

    _render_exchange_status_table(payload)


@app.command("schedule")
def status_schedule(
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """Show exchange schedule and maintenance windows."""
    from kalshi_research.api import KalshiPublicClient

    async def _fetch() -> dict[str, object]:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                schedule = await client.get_exchange_schedule()
            except KalshiAPIError as e:
                console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
                raise typer.Exit(1) from None
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        return schedule.model_dump(mode="json")

    payload = run_async(_fetch())

    if output_json:
        typer.echo(json.dumps(payload, indent=2, default=str))
        return

    _render_exchange_schedule(payload)


@app.command("announcements")
def status_announcements(
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """Show exchange announcements."""
    from kalshi_research.api import KalshiPublicClient

    async def _fetch() -> dict[str, object]:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                announcements = await client.get_exchange_announcements()
            except KalshiAPIError as e:
                console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
                raise typer.Exit(1) from None
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        return announcements.model_dump(mode="json")

    payload = run_async(_fetch())

    if output_json:
        typer.echo(json.dumps(payload, indent=2, default=str))
        return

    announcements = payload.get("announcements")
    if not isinstance(announcements, list) or not announcements:
        console.print("[yellow]No announcements returned.[/yellow]")
        return

    table = Table(title="Exchange Announcements")
    table.add_column("When", style="cyan", no_wrap=True)
    table.add_column("Status", style="green", no_wrap=True)
    table.add_column("Type", style="magenta", no_wrap=True)
    table.add_column("Message", style="white")

    for item in announcements[:50]:
        if not isinstance(item, dict):
            continue
        when = str(item.get("delivery_time") or "")
        status_value = str(item.get("status") or "")
        type_value = str(item.get("type") or "")
        message = str(item.get("message") or "")
        table.add_row(when, status_value, type_value, message)

    console.print(table)
