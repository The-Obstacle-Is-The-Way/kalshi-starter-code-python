from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from kalshi_research.api.config import Environment
from kalshi_research.api.models.order import OrderResponse
from kalshi_research.execution import TradeExecutor, TradeSafetyError

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.asyncio
async def test_trade_executor_defaults_to_dry_run(tmp_path: Path) -> None:
    audit_path = tmp_path / "trade_audit.jsonl"

    client = AsyncMock()
    client.create_order = AsyncMock(
        return_value=OrderResponse(order_id="dry-run-123", order_status="simulated")
    )

    executor = TradeExecutor(
        client,
        live=False,
        environment=Environment.DEMO,
        require_confirmation=False,
        audit_log_path=audit_path,
    )

    response = await executor.create_order(
        ticker="TEST-TICKER",
        side="yes",
        action="buy",
        count=10,
        yes_price_cents=55,
    )

    assert response.order_id == "dry-run-123"
    client.create_order.assert_awaited_once()
    assert client.create_order.call_args.kwargs["dry_run"] is True

    lines = audit_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["mode"] == "dry_run"
    assert event["environment"] == "demo"
    assert event["checks"]["passed"] is True


@pytest.mark.asyncio
async def test_trade_executor_live_requires_confirmation_callback(tmp_path: Path) -> None:
    audit_path = tmp_path / "trade_audit.jsonl"

    client = AsyncMock()
    client.create_order = AsyncMock()

    executor = TradeExecutor(
        client,
        live=True,
        environment=Environment.DEMO,
        require_confirmation=True,
        confirm=None,
        audit_log_path=audit_path,
    )

    with pytest.raises(TradeSafetyError):
        await executor.create_order(
            ticker="TEST-TICKER",
            side="yes",
            action="buy",
            count=1,
            yes_price_cents=55,
        )

    client.create_order.assert_not_awaited()
    event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[0])
    assert event["mode"] == "live"
    assert event["checks"]["passed"] is False
    assert "missing_confirmation_callback" in event["checks"]["failures"]


@pytest.mark.asyncio
async def test_trade_executor_live_confirmation_allows_trade(tmp_path: Path) -> None:
    audit_path = tmp_path / "trade_audit.jsonl"

    client = AsyncMock()
    client.create_order = AsyncMock(
        return_value=OrderResponse(order_id="order-1", order_status="resting")
    )

    confirm = MagicMock(return_value=True)

    executor = TradeExecutor(
        client,
        live=True,
        environment=Environment.DEMO,
        require_confirmation=True,
        confirm=confirm,
        audit_log_path=audit_path,
    )

    response = await executor.create_order(
        ticker="TEST-TICKER",
        side="yes",
        action="buy",
        count=1,
        yes_price_cents=55,
    )

    assert response.order_id == "order-1"
    confirm.assert_called_once()
    client.create_order.assert_awaited_once()
    assert client.create_order.call_args.kwargs["dry_run"] is False
    event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[0])
    assert event["checks"]["passed"] is True


@pytest.mark.asyncio
async def test_trade_executor_rejects_price_out_of_bounds(tmp_path: Path) -> None:
    audit_path = tmp_path / "trade_audit.jsonl"

    client = AsyncMock()
    client.create_order = AsyncMock()

    executor = TradeExecutor(
        client,
        live=False,
        environment=Environment.DEMO,
        require_confirmation=False,
        audit_log_path=audit_path,
    )

    with pytest.raises(TradeSafetyError):
        await executor.create_order(
            ticker="TEST-TICKER",
            side="yes",
            action="buy",
            count=1,
            yes_price_cents=0,
        )

    client.create_order.assert_not_awaited()
    event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[0])
    assert event["checks"]["passed"] is False
    assert "price_out_of_bounds" in event["checks"]["failures"]


@pytest.mark.asyncio
async def test_trade_executor_rejects_max_order_risk_exceeded(tmp_path: Path) -> None:
    audit_path = tmp_path / "trade_audit.jsonl"

    client = AsyncMock()
    client.create_order = AsyncMock()

    executor = TradeExecutor(
        client,
        live=False,
        environment=Environment.DEMO,
        require_confirmation=False,
        audit_log_path=audit_path,
        max_order_risk_usd=0.50,
    )

    with pytest.raises(TradeSafetyError):
        await executor.create_order(
            ticker="TEST-TICKER",
            side="yes",
            action="buy",
            count=1,
            yes_price_cents=55,  # max-loss-per-contract = 55c => $0.55
        )

    client.create_order.assert_not_awaited()
    event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[-1])
    assert event["checks"]["passed"] is False
    assert "max_order_risk_exceeded" in event["checks"]["failures"]


@pytest.mark.asyncio
async def test_trade_executor_live_rejects_kill_switch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    audit_path = tmp_path / "trade_audit.jsonl"

    monkeypatch.setenv("KALSHI_TRADE_KILL_SWITCH", "1")

    client = AsyncMock()
    client.create_order = AsyncMock()

    executor = TradeExecutor(
        client,
        live=True,
        environment=Environment.DEMO,
        require_confirmation=False,
        audit_log_path=audit_path,
    )

    with pytest.raises(TradeSafetyError):
        await executor.create_order(
            ticker="TEST-TICKER",
            side="yes",
            action="buy",
            count=1,
            yes_price_cents=55,
        )

    client.create_order.assert_not_awaited()
    event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[-1])
    assert event["checks"]["passed"] is False
    assert "kill_switch_enabled" in event["checks"]["failures"]


@pytest.mark.asyncio
async def test_trade_executor_live_rejects_production_without_allow(
    tmp_path: Path,
) -> None:
    audit_path = tmp_path / "trade_audit.jsonl"

    client = AsyncMock()
    client.create_order = AsyncMock()

    executor = TradeExecutor(
        client,
        live=True,
        environment=Environment.PRODUCTION,
        allow_production=False,
        require_confirmation=False,
        audit_log_path=audit_path,
    )

    with pytest.raises(TradeSafetyError):
        await executor.create_order(
            ticker="TEST-TICKER",
            side="yes",
            action="buy",
            count=1,
            yes_price_cents=55,
        )

    client.create_order.assert_not_awaited()
    event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[-1])
    assert event["checks"]["passed"] is False
    assert "production_trading_disabled" in event["checks"]["failures"]


@pytest.mark.asyncio
async def test_trade_executor_live_rejects_max_orders_per_day_exceeded(tmp_path: Path) -> None:
    audit_path = tmp_path / "trade_audit.jsonl"

    fixed_now = datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC)
    audit_path.write_text(
        "\n".join(
            [
                json.dumps({"mode": "live", "timestamp": fixed_now.isoformat()}),
                json.dumps({"mode": "live", "timestamp": fixed_now.isoformat()}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    client = AsyncMock()
    client.create_order = AsyncMock()

    executor = TradeExecutor(
        client,
        live=True,
        environment=Environment.DEMO,
        require_confirmation=False,
        max_orders_per_day=2,
        audit_log_path=audit_path,
        clock=lambda: fixed_now,
    )

    with pytest.raises(TradeSafetyError):
        await executor.create_order(
            ticker="TEST-TICKER",
            side="yes",
            action="buy",
            count=1,
            yes_price_cents=55,
        )

    client.create_order.assert_not_awaited()
    event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[-1])
    assert event["checks"]["passed"] is False
    assert "max_orders_per_day_exceeded" in event["checks"]["failures"]
