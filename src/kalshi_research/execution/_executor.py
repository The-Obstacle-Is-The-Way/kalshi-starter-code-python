"""Safe-by-default wrapper around Kalshi trading endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

import structlog

from kalshi_research.api.config import Environment, get_config
from kalshi_research.api.models.order import OrderAction, OrderResponse, OrderSide
from kalshi_research.execution._checks import (
    KILL_SWITCH_ENV,
    _count_live_orders_today,
    check_kill_switch,
    check_production_gating,
    run_common_checks,
)
from kalshi_research.execution._orchestration import (
    CheckConfig,
    ProviderConfig,
    run_live_checks,
)
from kalshi_research.execution.audit import TradeAuditLogger
from kalshi_research.execution.models import TradeAuditEvent, TradeChecks
from kalshi_research.paths import DEFAULT_TRADE_AUDIT_LOG

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from kalshi_research.analysis.liquidity import LiquidityGrade
    from kalshi_research.api.client import KalshiClient
    from kalshi_research.api.models.portfolio import CancelOrderResponse
    from kalshi_research.execution._protocols import (
        DailyBudgetTracker,
        MarketProvider,
        OrderbookProvider,
        PositionProvider,
    )


logger = structlog.get_logger()


class TradeSafetyError(RuntimeError):
    """Raised when a trade attempt fails safety checks."""


def _utc_now() -> datetime:
    return datetime.now(UTC)


class TradeExecutor:
    """Safety harness for trading operations (Phase 1 + Phase 2).

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

    # Expose for tests that need to reference the env var name
    KILL_SWITCH_ENV = KILL_SWITCH_ENV

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
        self._clock = clock

        self._audit = TradeAuditLogger(audit_log_path)

        # Build config objects for check functions
        self._check_config = CheckConfig(
            max_order_risk_usd=max_order_risk_usd,
            max_orders_per_day=max_orders_per_day,
            require_confirmation=require_confirmation,
            confirm=confirm,
            max_price_deviation_cents=max_price_deviation_cents,
            max_daily_loss_usd=max_daily_loss_usd,
            max_notional_usd=max_notional_usd,
            max_position_contracts=max_position_contracts,
            max_slippage_pct=max_slippage_pct,
            min_liquidity_grade=min_liquidity_grade,
        )

        self._provider_config = ProviderConfig(
            position_provider=position_provider,
            budget_tracker=budget_tracker,
            orderbook_provider=orderbook_provider,
            market_provider=market_provider,
        )

    @property
    def live(self) -> bool:
        """Return whether this executor will place live trades (vs dry-run)."""
        return self._live

    @property
    def audit_log_path(self) -> Path:
        """Return the JSONL audit log path used by this executor."""
        return self._audit.path

    def _count_live_orders_today(self) -> int:
        """Count live orders placed today (for backward compat with tests)."""
        return _count_live_orders_today(self._audit.path, self._clock)

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

        estimated_risk_usd, failures = run_common_checks(
            count=count,
            yes_price_cents=yes_price_cents,
            max_order_risk_usd=self._check_config.max_order_risk_usd,
        )
        if self._live:
            live_failures = await run_live_checks(
                ticker=ticker,
                side=resolved_side,
                action=resolved_action,
                count=count,
                yes_price_cents=yes_price_cents,
                estimated_risk_usd=estimated_risk_usd,
                environment=self._environment,
                allow_production=self._allow_production,
                audit_log_path=self._audit.path,
                clock=self._clock,
                check_config=self._check_config,
                provider_config=self._provider_config,
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
            # INTENTIONALLY BROAD: This catch exists solely for audit logging, not handling.
            # The exception is ALWAYS re-raised - we just capture the error message first.
            # Narrowing would miss unexpected failures in the audit trail.
            # Safety: No silent failure risk because the exception propagates.
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
                max_order_risk_usd=self._check_config.max_order_risk_usd,
                estimated_order_risk_usd=estimated_risk_usd,
                client_order_id=client_order_id,
                order_id=response.order_id if response is not None else None,
                checks=checks,
                error=error,
            )
            # Best-effort audit logging: don't mask the original exception if write fails
            try:
                self._audit.write(event)
            except Exception:
                logger.exception("audit_write_failed", ticker=ticker, mode=mode)

    async def cancel_order(self, order_id: str, dry_run: bool | None = None) -> CancelOrderResponse:
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

        if failure := check_kill_switch():
            failures.append(failure)

        if failure := check_production_gating(self._environment, self._allow_production):
            failures.append(failure)

        if failures:
            raise TradeSafetyError("; ".join(failures))

        resolved_dry_run = (not self._live) if dry_run is None else dry_run
        return await self._client.cancel_order(order_id, dry_run=resolved_dry_run)

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

        if failure := check_kill_switch():
            failures.append(failure)

        if failure := check_production_gating(self._environment, self._allow_production):
            failures.append(failure)

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
