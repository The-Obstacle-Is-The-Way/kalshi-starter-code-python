"""Safe-by-default wrapper around Kalshi trading endpoints."""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from kalshi_research.api.config import Environment, get_config
from kalshi_research.api.models.order import OrderAction, OrderResponse, OrderSide
from kalshi_research.execution.audit import TradeAuditLogger
from kalshi_research.execution.models import TradeAuditEvent, TradeChecks
from kalshi_research.paths import DEFAULT_TRADE_AUDIT_LOG

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from kalshi_research.api.client import KalshiClient


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
    Safety harness for trading operations.

    - Defaults to `live=False` (dry-run mode).
    - Writes an append-only JSONL audit event for every attempt.
    - Enforces basic guardrails (env gating, kill switch, limits, confirmation).
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
    ) -> None:
        self._client = client
        self._live = live

        resolved_env = environment or get_config().environment
        self._environment = resolved_env
        self._allow_production = allow_production

        self._max_order_risk_usd = max_order_risk_usd
        self._max_orders_per_day = max_orders_per_day
        self._require_confirmation = require_confirmation
        self._confirm = confirm
        self._clock = clock

        self._audit = TradeAuditLogger(audit_log_path)

    @property
    def live(self) -> bool:
        return self._live

    @property
    def audit_log_path(self) -> Path:
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
        failures: list[str] = []

        if yes_price_cents < 1 or yes_price_cents > 99:
            failures.append("price_out_of_bounds")
        if count <= 0:
            failures.append("count_not_positive")

        estimated_risk_usd = _estimate_order_risk_usd(count=count, yes_price_cents=yes_price_cents)
        if estimated_risk_usd > self._max_order_risk_usd:
            failures.append("max_order_risk_exceeded")

        return estimated_risk_usd, failures

    def _run_live_checks(
        self,
        *,
        ticker: str,
        side: OrderSide,
        action: OrderAction,
        count: int,
        yes_price_cents: int,
        estimated_risk_usd: float,
    ) -> list[str]:
        failures: list[str] = []

        if os.getenv(self.KILL_SWITCH_ENV) == "1":
            failures.append("kill_switch_enabled")

        if self._environment == Environment.PRODUCTION and not self._allow_production:
            failures.append("production_trading_disabled")

        if self._max_orders_per_day > 0:
            live_orders_today = self._count_live_orders_today()
            if live_orders_today >= self._max_orders_per_day:
                failures.append("max_orders_per_day_exceeded")

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
            failures.extend(
                self._run_live_checks(
                    ticker=ticker,
                    side=resolved_side,
                    action=resolved_action,
                    count=count,
                    yes_price_cents=yes_price_cents,
                    estimated_risk_usd=estimated_risk_usd,
                )
            )

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
