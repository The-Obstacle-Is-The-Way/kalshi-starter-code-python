"""Safe-by-default wrapper around Kalshi trading endpoints."""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, Protocol

from kalshi_research.analysis.liquidity import (
    LiquidityGrade,
    enforce_max_slippage,
    liquidity_score,
)
from kalshi_research.api.config import Environment, get_config
from kalshi_research.api.models.order import OrderAction, OrderResponse, OrderSide
from kalshi_research.execution.audit import TradeAuditLogger
from kalshi_research.execution.models import TradeAuditEvent, TradeChecks
from kalshi_research.paths import DEFAULT_TRADE_AUDIT_LOG

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from kalshi_research.api.client import KalshiClient
    from kalshi_research.api.models.market import Market
    from kalshi_research.api.models.orderbook import Orderbook


class PositionProvider(Protocol):
    """Protocol for querying current position state."""

    async def get_position_quantity(self, ticker: str, side: OrderSide) -> int:
        """Return the current signed position quantity for a ticker+side.

        Returns 0 if no position exists.
        """
        ...


class DailyBudgetTracker(Protocol):
    """Protocol for tracking daily spending and losses."""

    async def get_daily_spend_usd(self) -> float:
        """Return total USD spent today (live orders)."""
        ...

    async def get_daily_loss_usd(self) -> float:
        """Return total realized loss today (positive = loss)."""
        ...


class OrderbookProvider(Protocol):
    """Protocol for fetching orderbook snapshots."""

    async def get_orderbook(self, ticker: str) -> Orderbook:
        """Fetch current orderbook for a market."""
        ...


class MarketProvider(Protocol):
    """Protocol for fetching market data."""

    async def get_market(self, ticker: str) -> Market:
        """Fetch market metadata."""
        ...


class TradeSafetyError(RuntimeError):
    """Raised when a trade attempt fails safety checks."""


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _estimate_order_risk_usd(*, count: int, yes_price_cents: int) -> float:
    """
    Conservative worst-case risk estimate for a binary contract order.

    Uses `max(yes_price, 100-yes_price)` as max-loss-per-contract (in cents).
    This is conservative for buys/sells and avoids side-specific complexity.
    """
    max_loss_cents = max(yes_price_cents, 100 - yes_price_cents)
    return (count * max_loss_cents) / 100.0


class TradeExecutor:
    """
    Safety harness for trading operations (Phase 1 + Phase 2).

    Phase 1 (Implemented):
    - Defaults to `live=False` (dry-run mode).
    - Writes an append-only JSONL audit event for every attempt.
    - Enforces basic guardrails (env gating, kill switch, limits, confirmation).

    Phase 2 (Implemented):
    - Fat-finger guard (midpoint deviation check).
    - Daily budget/loss tracking.
    - Position caps (max contracts per market).
    - Liquidity-aware sizing (slippage limits).
    """

    KILL_SWITCH_ENV = "KALSHI_TRADE_KILL_SWITCH"

    def __init__(
        self,
        client: KalshiClient,
        *,
        live: bool = False,
        environment: Environment | None = None,
        allow_production: bool = False,
        max_order_risk_usd: float = 200.0,
        max_orders_per_day: int = 25,
        require_confirmation: bool = True,
        confirm: Callable[[str], bool] | None = None,
        audit_log_path: Path = DEFAULT_TRADE_AUDIT_LOG,
        clock: Callable[[], datetime] = _utc_now,
        # Phase 2 parameters
        max_price_deviation_cents: int = 10,
        max_daily_loss_usd: float = 50.0,
        max_notional_usd: float = 200.0,
        max_position_contracts: int = 100,
        max_slippage_pct: float = 5.0,
        min_liquidity_grade: LiquidityGrade | None = None,
        position_provider: PositionProvider | None = None,
        budget_tracker: DailyBudgetTracker | None = None,
        orderbook_provider: OrderbookProvider | None = None,
        market_provider: MarketProvider | None = None,
    ) -> None:
        self._client = client
        self._live = live

        resolved_env = environment or get_config().environment
        self._environment = resolved_env
        self._allow_production = allow_production

        # Phase 1 parameters
        self._max_order_risk_usd = max_order_risk_usd
        self._max_orders_per_day = max_orders_per_day
        self._require_confirmation = require_confirmation
        self._confirm = confirm
        self._clock = clock

        # Phase 2 parameters
        self._max_price_deviation_cents = max_price_deviation_cents
        self._max_daily_loss_usd = max_daily_loss_usd
        self._max_notional_usd = max_notional_usd
        self._max_position_contracts = max_position_contracts
        self._max_slippage_pct = max_slippage_pct
        self._min_liquidity_grade = min_liquidity_grade

        # Phase 2 providers (optional, for advanced safety checks)
        self._position_provider = position_provider
        self._budget_tracker = budget_tracker
        self._orderbook_provider = orderbook_provider
        self._market_provider = market_provider

        self._audit = TradeAuditLogger(audit_log_path)

    @property
    def live(self) -> bool:
        """Return whether this executor will place live trades (vs dry-run)."""
        return self._live

    @property
    def audit_log_path(self) -> Path:
        """Return the JSONL audit log path used by this executor."""
        return self._audit.path

    def _count_live_orders_today(self) -> int:
        if not self._audit.path.exists():
            return 0

        today = self._clock().date()
        count = 0
        with self._audit.path.open(encoding="utf-8") as f:
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

    def _run_common_checks(self, *, count: int, yes_price_cents: int) -> tuple[float, list[str]]:
        """Validate basic order constraints shared by dry-run and live modes.

        Args:
            count: Number of contracts to trade.
            yes_price_cents: YES price in cents (1-99).

        Returns:
            Tuple of (`estimated_risk_usd`, `failures`) where failures is a list of internal
            failure codes.
        """
        failures: list[str] = []

        if yes_price_cents < 1 or yes_price_cents > 99:
            failures.append("price_out_of_bounds")
        if count <= 0:
            failures.append("count_not_positive")

        estimated_risk_usd = _estimate_order_risk_usd(count=count, yes_price_cents=yes_price_cents)
        if estimated_risk_usd > self._max_order_risk_usd:
            failures.append("max_order_risk_exceeded")

        return estimated_risk_usd, failures

    async def _run_live_checks(  # noqa: PLR0912, PLR0915
        self,
        *,
        ticker: str,
        side: OrderSide,
        action: OrderAction,
        count: int,
        yes_price_cents: int,
        estimated_risk_usd: float,
    ) -> list[str]:
        """Validate live-trading guardrails that should block order placement.

        Args:
            ticker: Market ticker to trade.
            side: Side to trade (YES/NO).
            action: Buy or sell.
            count: Number of contracts to trade.
            yes_price_cents: YES price in cents (1-99).
            estimated_risk_usd: Estimated USD risk for this order.

        Returns:
            List of internal failure codes for any guardrails that failed.
        """
        failures: list[str] = []

        # Phase 1 checks
        if os.getenv(self.KILL_SWITCH_ENV) == "1":
            failures.append("kill_switch_enabled")

        if self._environment == Environment.PRODUCTION and not self._allow_production:
            failures.append("production_trading_disabled")

        if self._max_orders_per_day > 0:
            live_orders_today = self._count_live_orders_today()
            if live_orders_today >= self._max_orders_per_day:
                failures.append("max_orders_per_day_exceeded")

        # Phase 2 checks
        if self._budget_tracker is not None:
            daily_loss = await self._budget_tracker.get_daily_loss_usd()
            if daily_loss >= self._max_daily_loss_usd:
                failures.append("max_daily_loss_exceeded")

            daily_spend = await self._budget_tracker.get_daily_spend_usd()
            if daily_spend + estimated_risk_usd > self._max_notional_usd:
                failures.append("max_notional_exceeded")

        if self._position_provider is not None:
            current_position = await self._position_provider.get_position_quantity(ticker, side)
            new_position_size = abs(
                current_position + (count if action == OrderAction.BUY else -count)
            )
            if new_position_size > self._max_position_contracts:
                failures.append("max_position_contracts_exceeded")

        if self._orderbook_provider is not None:
            try:
                orderbook = await self._orderbook_provider.get_orderbook(ticker)
                midpoint = orderbook.midpoint
                if midpoint is not None:
                    midpoint_cents = float(midpoint)
                    deviation = abs(yes_price_cents - midpoint_cents)
                    if deviation > self._max_price_deviation_cents:
                        failures.append("fat_finger_deviation_exceeded")

                # Liquidity-aware sizing: check slippage
                if action == OrderAction.BUY:
                    try:
                        enforce_max_slippage(
                            orderbook,
                            side.value,
                            action.value,
                            quantity=count,
                            max_slippage_pct=self._max_slippage_pct,
                        )
                    except Exception:
                        failures.append("slippage_limit_exceeded")
            except Exception:
                # If we can't fetch orderbook, don't block but we can't validate
                pass

        if self._market_provider is not None and self._orderbook_provider is not None:
            try:
                market = await self._market_provider.get_market(ticker)
                orderbook = await self._orderbook_provider.get_orderbook(ticker)
                analysis = liquidity_score(market, orderbook)

                if self._min_liquidity_grade is not None:
                    grade_order = {
                        LiquidityGrade.ILLIQUID: 0,
                        LiquidityGrade.THIN: 1,
                        LiquidityGrade.MODERATE: 2,
                        LiquidityGrade.LIQUID: 3,
                    }
                    if grade_order[analysis.grade] < grade_order[self._min_liquidity_grade]:
                        failures.append("liquidity_grade_too_low")
            except Exception:
                # If we can't compute liquidity, don't block
                pass

        # Confirmation (Phase 1, but runs last)
        if self._require_confirmation:
            if self._confirm is None:
                failures.append("missing_confirmation_callback")
            else:
                summary = (
                    f"{action.value.upper()} {count} {side.value.upper()} "
                    f"{ticker} @ {yes_price_cents}¢ (risk≈${estimated_risk_usd:.2f})"
                )
                if not bool(self._confirm(summary)):
                    failures.append("confirmation_declined")

        return failures

    async def create_order(
        self,
        *,
        ticker: str,
        side: Literal["yes", "no"] | OrderSide,
        action: Literal["buy", "sell"] | OrderAction,
        count: int,
        yes_price_cents: int,
        client_order_id: str | None = None,
        expiration_ts: int | None = None,
    ) -> OrderResponse:
        """Create an order through the safety harness.

        This method:
        - Validates basic constraints (count, price bounds, risk estimate).
        - Enforces live-trading guardrails (kill switch, production gating, daily limits,
          and optional confirmation).
        - Always writes an audit event (success or failure).

        Args:
            ticker: Market ticker to trade.
            side: `"yes"`/`"no"` or `OrderSide`.
            action: `"buy"`/`"sell"` or `OrderAction`.
            count: Number of contracts.
            yes_price_cents: YES price in cents (1-99).
            client_order_id: Optional client-assigned ID (UUID is generated if omitted).
            expiration_ts: Optional expiration timestamp for the order.

        Returns:
            `OrderResponse` from the Kalshi API client.

        Raises:
            TradeSafetyError: If safety checks fail.
            Exception: Propagates API/client errors from the underlying `KalshiClient`.
        """
        now = self._clock()
        mode: Literal["dry_run", "live"] = "live" if self._live else "dry_run"

        resolved_side = OrderSide(side) if isinstance(side, str) else side
        resolved_action = OrderAction(action) if isinstance(action, str) else action

        if client_order_id is None:
            client_order_id = str(uuid.uuid4())

        estimated_risk_usd, failures = self._run_common_checks(
            count=count,
            yes_price_cents=yes_price_cents,
        )
        if self._live:
            live_failures = await self._run_live_checks(
                ticker=ticker,
                side=resolved_side,
                action=resolved_action,
                count=count,
                yes_price_cents=yes_price_cents,
                estimated_risk_usd=estimated_risk_usd,
            )
            failures.extend(live_failures)

        checks = TradeChecks(passed=not failures, failures=failures)
        response: OrderResponse | None = None
        error: str | None = None

        try:
            if failures:
                raise TradeSafetyError("; ".join(failures))

            response = await self._client.create_order(
                ticker=ticker,
                side=resolved_side,
                action=resolved_action,
                count=count,
                price=yes_price_cents,
                client_order_id=client_order_id,
                expiration_ts=expiration_ts,
                dry_run=not self._live,
            )
            return response
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            event = TradeAuditEvent(
                timestamp=now,
                mode=mode,
                environment=self._environment,
                ticker=ticker,
                side=resolved_side,
                action=resolved_action,
                count=count,
                yes_price_cents=yes_price_cents,
                max_order_risk_usd=self._max_order_risk_usd,
                estimated_order_risk_usd=estimated_risk_usd,
                client_order_id=client_order_id,
                order_id=response.order_id if response is not None else None,
                checks=checks,
                error=error,
            )
            self._audit.write(event)

    async def cancel_order(self, order_id: str, dry_run: bool | None = None) -> OrderResponse:
        """Cancel an existing order through the safety harness.

        Phase 2 addition: This wrapper ensures kill switch and environment checks apply
        to cancellation operations as well.

        Args:
            order_id: The order ID to cancel.
            dry_run: If provided, overrides the executor's live mode for this operation.

        Returns:
            `CancelOrderResponse` from the Kalshi API client (covariant with OrderResponse).

        Raises:
            TradeSafetyError: If safety checks fail (kill switch, production gating).
            Exception: Propagates API/client errors from the underlying `KalshiClient`.
        """
        failures: list[str] = []

        if os.getenv(self.KILL_SWITCH_ENV) == "1":
            failures.append("kill_switch_enabled")

        if self._environment == Environment.PRODUCTION and not self._allow_production:
            failures.append("production_trading_disabled")

        if failures:
            raise TradeSafetyError("; ".join(failures))

        resolved_dry_run = (not self._live) if dry_run is None else dry_run
        response = await self._client.cancel_order(order_id, dry_run=resolved_dry_run)
        # Type system doesn't know CancelOrderResponse is compatible with OrderResponse.
        # For now, we return the actual cancel response.
        return response  # type: ignore[return-value]

    async def amend_order(
        self,
        order_id: str,
        ticker: str,
        side: Literal["yes", "no"] | OrderSide,
        action: Literal["buy", "sell"] | OrderAction,
        client_order_id: str,
        updated_client_order_id: str,
        *,
        count: int | None = None,
        price: int | None = None,
        dry_run: bool | None = None,
    ) -> OrderResponse:
        """Amend an existing order through the safety harness.

        Phase 2 addition: This wrapper ensures kill switch and environment checks apply
        to amendment operations.

        Args:
            order_id: The order ID to amend.
            ticker: Market ticker.
            side: Order side (yes/no).
            action: Order action (buy/sell).
            client_order_id: Original client_order_id from the order creation.
            updated_client_order_id: New unique client_order_id for the amendment.
            count: New quantity (optional).
            price: New price in cents (optional).
            dry_run: If provided, overrides the executor's live mode for this operation.

        Returns:
            `OrderResponse` from the Kalshi API client.

        Raises:
            TradeSafetyError: If safety checks fail (kill switch, production gating).
            Exception: Propagates API/client errors from the underlying `KalshiClient`.
        """
        failures: list[str] = []

        if os.getenv(self.KILL_SWITCH_ENV) == "1":
            failures.append("kill_switch_enabled")

        if self._environment == Environment.PRODUCTION and not self._allow_production:
            failures.append("production_trading_disabled")

        if failures:
            raise TradeSafetyError("; ".join(failures))

        resolved_dry_run = (not self._live) if dry_run is None else dry_run
        return await self._client.amend_order(
            order_id=order_id,
            ticker=ticker,
            side=side,
            action=action,
            client_order_id=client_order_id,
            updated_client_order_id=updated_client_order_id,
            count=count,
            price=price,
            dry_run=resolved_dry_run,
        )
