"""Portfolio balance command - view account balance."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from kalshi_research.cli.portfolio._helpers import (
    require_auth_env,
    resolve_rate_tier_override,
    validate_environment_override,
)
from kalshi_research.cli.utils import console, exit_kalshi_api_error, run_async


def portfolio_balance(
    environment: Annotated[
        str | None,
        typer.Option("--env", help="Override global environment (demo or prod)."),
    ] = None,
    rate_tier: Annotated[
        str | None,
        typer.Option(
            "--rate-tier",
            help=(
                "API rate limit tier (basic/advanced/premier/prime). "
                "Defaults to KALSHI_RATE_TIER or basic."
            ),
            show_default=False,
        ),
    ] = None,
) -> None:
    """View account balance."""
    from kalshi_research.api.exceptions import KalshiAPIError
    from kalshi_research.cli.client_factory import authed_client

    environment_override = validate_environment_override(environment)
    key_id, private_key_path, private_key_b64 = require_auth_env(
        purpose="Balance", environment=environment_override
    )
    rate_tier_override = resolve_rate_tier_override(rate_tier)

    async def _balance() -> None:
        from kalshi_research.api.models.portfolio import (  # noqa: TC001
            PortfolioBalance,
        )

        balance: PortfolioBalance | None = None
        try:
            async with authed_client(
                key_id=key_id,
                private_key_path=private_key_path,
                private_key_b64=private_key_b64,
                environment=environment_override,
                rate_tier=rate_tier_override,
            ) as client:
                try:
                    balance = await client.get_balance()
                except KalshiAPIError as e:
                    exit_kalshi_api_error(e)
        except (OSError, ValueError) as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

        if not balance:
            console.print("[yellow]No balance data returned[/yellow]")
            return

        table = Table(title="Account Balance")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        # Convert Pydantic model to dict for display
        balance_dict = balance.model_dump()
        for k, v in sorted(balance_dict.items()):
            table.add_row(str(k), str(v))
        console.print(table)

    run_async(_balance())
