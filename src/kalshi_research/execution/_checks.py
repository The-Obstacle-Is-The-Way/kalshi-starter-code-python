"""Safety check implementations for the trade execution harness."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import TYPE_CHECKING

import httpx
import structlog

from kalshi_research.analysis.liquidity import (
    LiquidityError,
    LiquidityGrade,
    enforce_max_slippage,
    liquidity_score,
)
from kalshi_research.api.config import Environment
from kalshi_research.api.exceptions import KalshiAPIError
from kalshi_research.api.models.order import OrderAction, OrderSide

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from kalshi_research.api.models.orderbook import Orderbook
    from kalshi_research.execution._protocols import (
        DailyBudgetTracker,
        MarketProvider,
        OrderbookProvider,
        PositionProvider,
    )

logger = structlog.get_logger()

# Environment variable name for the kill switch
KILL_SWITCH_ENV = "KALSHI_TRADE_KILL_SWITCH"


def estimate_order_risk_usd(*, count: int, yes_price_cents: int) -> float:
    """Estimate worst-case risk for a binary contract order.

    Uses `max(yes_price, 100-yes_price)` as max-loss-per-contract (in cents).
    This is conservative for buys/sells and avoids side-specific complexity.
    """
    max_loss_cents = max(yes_price_cents, 100 - yes_price_cents)
    return (count * max_loss_cents) / 100.0


def run_common_checks(
    *,
    count: int,
    yes_price_cents: int,
    max_order_risk_usd: float,
) -> tuple[float, list[str]]:
    """Validate basic order constraints shared by dry-run and live modes.

    Args:
        count: Number of contracts to trade.
        yes_price_cents: YES price in cents (1-99).
        max_order_risk_usd: Maximum allowed order risk in USD.

    Returns:
        Tuple of (`estimated_risk_usd`, `failures`) where failures is a list of
        internal failure codes.
    """
    failures: list[str] = []

    if yes_price_cents < 1 or yes_price_cents > 99:
        failures.append("price_out_of_bounds")
    if count <= 0:
        failures.append("count_not_positive")

    estimated_risk_usd = estimate_order_risk_usd(count=count, yes_price_cents=yes_price_cents)
    if estimated_risk_usd > max_order_risk_usd:
        failures.append("max_order_risk_exceeded")

    return estimated_risk_usd, failures


def check_kill_switch() -> str | None:
    """Check if trading kill switch is enabled."""
    if os.getenv(KILL_SWITCH_ENV) == "1":
        return "kill_switch_enabled"
    return None


def check_production_gating(environment: Environment, allow_production: bool) -> str | None:
    """Check if production trading is allowed."""
    if environment == Environment.PRODUCTION and not allow_production:
        return "production_trading_disabled"
    return None


def check_daily_order_limit(
    *,
    audit_log_path: Path,
    clock: Callable[[], datetime],
    max_orders_per_day: int,
) -> str | None:
    """Check if daily order limit has been reached."""
    if max_orders_per_day <= 0:
        return None

    live_orders_today = _count_live_orders_today(audit_log_path, clock)
    if live_orders_today >= max_orders_per_day:
        return "max_orders_per_day_exceeded"
    return None


def _count_live_orders_today(audit_log_path: Path, clock: Callable[[], datetime]) -> int:
    """Count live orders placed today from the audit log."""
    if not audit_log_path.exists():
        return 0

    today = clock().date()
    count = 0
    with audit_log_path.open(encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(raw, dict):
                continue
            if raw.get("mode") != "live":
                continue
            ts = raw.get("timestamp")
            if not isinstance(ts, str):
                continue
            try:
                if datetime.fromisoformat(ts).date() == today:
                    count += 1
            except ValueError:
                continue
    return count


async def check_budget_limits(
    *,
    estimated_risk_usd: float,
    max_daily_loss_usd: float,
    max_notional_usd: float,
    budget_tracker: DailyBudgetTracker | None,
) -> list[str]:
    """Check daily loss and notional limits."""
    failures: list[str] = []
    if budget_tracker is None:
        return failures

    daily_loss = await budget_tracker.get_daily_loss_usd()
    if daily_loss >= max_daily_loss_usd:
        failures.append("max_daily_loss_exceeded")

    daily_spend = await budget_tracker.get_daily_spend_usd()
    if daily_spend + estimated_risk_usd > max_notional_usd:
        failures.append("max_notional_exceeded")

    return failures


async def check_position_cap(
    ticker: str,
    side: OrderSide,
    action: OrderAction,
    count: int,
    *,
    max_position_contracts: int,
    position_provider: PositionProvider | None,
) -> str | None:
    """Check if order would exceed position cap."""
    if position_provider is None:
        return None

    current_position = await position_provider.get_position_quantity(ticker, side)
    new_position_size = abs(current_position + (count if action == OrderAction.BUY else -count))
    if new_position_size > max_position_contracts:
        return "max_position_contracts_exceeded"
    return None


async def check_orderbook_safety(
    ticker: str,
    side: OrderSide,
    action: OrderAction,
    count: int,
    yes_price_cents: int,
    *,
    max_price_deviation_cents: int,
    max_slippage_pct: float,
    orderbook_provider: OrderbookProvider | None,
) -> tuple[list[str], Orderbook | None]:
    """Check fat-finger deviation and slippage limits.

    Returns:
        Tuple of (failures, orderbook) where orderbook may be None if provider unavailable.
    """
    failures: list[str] = []
    orderbook: Orderbook | None = None

    if orderbook_provider is None:
        return failures, orderbook

    try:
        orderbook = await orderbook_provider.get_orderbook(ticker)

        # Fat-finger deviation check
        midpoint = orderbook.midpoint
        if midpoint is not None:
            midpoint_cents = float(midpoint)
            deviation = abs(yes_price_cents - midpoint_cents)
            if deviation > max_price_deviation_cents:
                failures.append("fat_finger_deviation_exceeded")

        # Slippage check (only for buys)
        if action == OrderAction.BUY:
            try:
                enforce_max_slippage(
                    orderbook,
                    side.value,
                    action.value,
                    quantity=count,
                    max_slippage_pct=max_slippage_pct,
                )
            except LiquidityError:
                failures.append("slippage_limit_exceeded")
    except (KalshiAPIError, httpx.HTTPError, httpx.TimeoutException) as exc:
        # Fail closed: when safety checks cannot be evaluated, block the trade.
        # Expected failures: API errors (4xx/5xx), network issues, timeouts.
        failures.append("orderbook_provider_failed")
        logger.warning(
            "orderbook_provider_failed",
            ticker=ticker,
            error_type=type(exc).__name__,
            error=str(exc),
        )

    return failures, orderbook


async def check_liquidity_grade(
    ticker: str,
    orderbook: Orderbook | None,
    *,
    min_liquidity_grade: LiquidityGrade | None,
    market_provider: MarketProvider | None,
) -> str | None:
    """Check if market meets minimum liquidity grade."""
    if min_liquidity_grade is None or market_provider is None or orderbook is None:
        return None

    try:
        market = await market_provider.get_market(ticker)
        analysis = liquidity_score(market, orderbook)

        grade_order = {
            LiquidityGrade.ILLIQUID: 0,
            LiquidityGrade.THIN: 1,
            LiquidityGrade.MODERATE: 2,
            LiquidityGrade.LIQUID: 3,
        }
        if grade_order[analysis.grade] < grade_order[min_liquidity_grade]:
            return "liquidity_grade_too_low"
    except (KalshiAPIError, httpx.HTTPError, httpx.TimeoutException) as exc:
        # Fail closed: when safety checks cannot be evaluated, block the trade.
        # Expected failures: API errors (4xx/5xx), network issues, timeouts.
        logger.warning(
            "liquidity_check_failed",
            ticker=ticker,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return "liquidity_check_failed"

    return None


def check_confirmation(
    ticker: str,
    side: OrderSide,
    action: OrderAction,
    count: int,
    yes_price_cents: int,
    estimated_risk_usd: float,
    *,
    require_confirmation: bool,
    confirm: Callable[[str], bool] | None,
) -> str | None:
    """Check user confirmation for the trade."""
    if not require_confirmation:
        return None

    if confirm is None:
        return "missing_confirmation_callback"

    summary = (
        f"{action.value.upper()} {count} {side.value.upper()} "
        f"{ticker} @ {yes_price_cents}\u00a2 (risk\u2248${estimated_risk_usd:.2f})"
    )
    if not bool(confirm(summary)):
        return "confirmation_declined"

    return None
