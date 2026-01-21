"""Orchestration and configuration for safety checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kalshi_research.execution._checks import (
    check_budget_limits,
    check_confirmation,
    check_daily_order_limit,
    check_kill_switch,
    check_liquidity_grade,
    check_orderbook_safety,
    check_position_cap,
    check_production_gating,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime
    from pathlib import Path

    from kalshi_research.analysis.liquidity import LiquidityGrade
    from kalshi_research.api.config import Environment
    from kalshi_research.api.models.order import OrderAction, OrderSide
    from kalshi_research.execution._protocols import (
        DailyBudgetTracker,
        MarketProvider,
        OrderbookProvider,
        PositionProvider,
    )


class CheckConfig:
    """Configuration for safety checks."""

    __slots__ = (
        "confirm",
        "max_daily_loss_usd",
        "max_notional_usd",
        "max_order_risk_usd",
        "max_orders_per_day",
        "max_position_contracts",
        "max_price_deviation_cents",
        "max_slippage_pct",
        "min_liquidity_grade",
        "require_confirmation",
    )

    def __init__(
        self,
        *,
        max_order_risk_usd: float,
        max_orders_per_day: int,
        require_confirmation: bool,
        confirm: Callable[[str], bool] | None,
        max_price_deviation_cents: int,
        max_daily_loss_usd: float,
        max_notional_usd: float,
        max_position_contracts: int,
        max_slippage_pct: float,
        min_liquidity_grade: LiquidityGrade | None,
    ) -> None:
        self.max_order_risk_usd = max_order_risk_usd
        self.max_orders_per_day = max_orders_per_day
        self.require_confirmation = require_confirmation
        self.confirm = confirm
        self.max_price_deviation_cents = max_price_deviation_cents
        self.max_daily_loss_usd = max_daily_loss_usd
        self.max_notional_usd = max_notional_usd
        self.max_position_contracts = max_position_contracts
        self.max_slippage_pct = max_slippage_pct
        self.min_liquidity_grade = min_liquidity_grade


class ProviderConfig:
    """Configuration for external providers."""

    __slots__ = (
        "budget_tracker",
        "market_provider",
        "orderbook_provider",
        "position_provider",
    )

    def __init__(
        self,
        *,
        position_provider: PositionProvider | None,
        budget_tracker: DailyBudgetTracker | None,
        orderbook_provider: OrderbookProvider | None,
        market_provider: MarketProvider | None,
    ) -> None:
        self.position_provider = position_provider
        self.budget_tracker = budget_tracker
        self.orderbook_provider = orderbook_provider
        self.market_provider = market_provider


async def run_live_checks(
    *,
    ticker: str,
    side: OrderSide,
    action: OrderAction,
    count: int,
    yes_price_cents: int,
    estimated_risk_usd: float,
    environment: Environment,
    allow_production: bool,
    audit_log_path: Path,
    clock: Callable[[], datetime],
    check_config: CheckConfig,
    provider_config: ProviderConfig,
) -> list[str]:
    """Validate live-trading guardrails that should block order placement.

    Returns:
        List of internal failure codes for any guardrails that failed.
    """
    failures: list[str] = []

    # Phase 1 checks (sync)
    if failure := check_kill_switch():
        failures.append(failure)

    if failure := check_production_gating(environment, allow_production):
        failures.append(failure)

    if failure := check_daily_order_limit(
        audit_log_path=audit_log_path,
        clock=clock,
        max_orders_per_day=check_config.max_orders_per_day,
    ):
        failures.append(failure)

    # Phase 2 checks (async)
    failures.extend(
        await check_budget_limits(
            estimated_risk_usd=estimated_risk_usd,
            max_daily_loss_usd=check_config.max_daily_loss_usd,
            max_notional_usd=check_config.max_notional_usd,
            budget_tracker=provider_config.budget_tracker,
        )
    )

    if failure := await check_position_cap(
        ticker,
        side,
        action,
        count,
        max_position_contracts=check_config.max_position_contracts,
        position_provider=provider_config.position_provider,
    ):
        failures.append(failure)

    orderbook_failures, orderbook = await check_orderbook_safety(
        ticker,
        side,
        action,
        count,
        yes_price_cents,
        max_price_deviation_cents=check_config.max_price_deviation_cents,
        max_slippage_pct=check_config.max_slippage_pct,
        orderbook_provider=provider_config.orderbook_provider,
    )
    failures.extend(orderbook_failures)

    if failure := await check_liquidity_grade(
        ticker,
        orderbook,
        min_liquidity_grade=check_config.min_liquidity_grade,
        market_provider=provider_config.market_provider,
    ):
        failures.append(failure)

    # Confirmation check (runs last)
    if failure := check_confirmation(
        ticker,
        side,
        action,
        count,
        yes_price_cents,
        estimated_risk_usd,
        require_confirmation=check_config.require_confirmation,
        confirm=check_config.confirm,
    ):
        failures.append(failure)

    return failures
