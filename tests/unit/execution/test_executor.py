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


def test_trade_executor_properties_expose_live_and_audit_path(tmp_path: Path) -> None:
    audit_path = tmp_path / "trade_audit.jsonl"

    executor = TradeExecutor(
        AsyncMock(),
        live=False,
        environment=Environment.DEMO,
        require_confirmation=False,
        audit_log_path=audit_path,
    )

    assert executor.live is False
    assert executor.audit_log_path == audit_path


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
async def test_trade_executor_live_confirmation_declined_rejects_trade(tmp_path: Path) -> None:
    audit_path = tmp_path / "trade_audit.jsonl"

    client = AsyncMock()
    client.create_order = AsyncMock()

    confirm = MagicMock(return_value=False)

    executor = TradeExecutor(
        client,
        live=True,
        environment=Environment.DEMO,
        require_confirmation=True,
        confirm=confirm,
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
    assert "confirmation_declined" in event["checks"]["failures"]


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
async def test_trade_executor_rejects_non_positive_count(tmp_path: Path) -> None:
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
            count=0,
            yes_price_cents=55,
        )

    event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[-1])
    assert "count_not_positive" in event["checks"]["failures"]


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


def test_trade_executor_counts_only_valid_live_entries_today(tmp_path: Path) -> None:
    fixed_now = datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC)
    audit_path = tmp_path / "trade_audit.jsonl"
    audit_path.write_text(
        "\n".join(
            [
                "",
                "not json",
                json.dumps([]),
                json.dumps({"mode": "dry_run", "timestamp": fixed_now.isoformat()}),
                json.dumps({"mode": "live", "timestamp": 123}),
                json.dumps({"mode": "live", "timestamp": "not-a-date"}),
                json.dumps({"mode": "live", "timestamp": fixed_now.isoformat()}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    executor = TradeExecutor(
        AsyncMock(),
        live=True,
        environment=Environment.DEMO,
        require_confirmation=False,
        audit_log_path=audit_path,
        clock=lambda: fixed_now,
    )

    assert executor._count_live_orders_today() == 1


# Phase 2 tests


@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_executor_daily_loss_cap_blocks_when_exceeded(tmp_path: Path) -> None:
    """Test that daily loss cap blocks orders when limit is reached."""
    from unittest.mock import AsyncMock

    audit_path = tmp_path / "trade_audit.jsonl"

    client = AsyncMock()
    client.create_order = AsyncMock()

    budget_tracker = AsyncMock()
    budget_tracker.get_daily_loss_usd = AsyncMock(return_value=60.0)
    budget_tracker.get_daily_spend_usd = AsyncMock(return_value=0.0)

    executor = TradeExecutor(
        client,
        live=True,
        environment=Environment.DEMO,
        require_confirmation=False,
        audit_log_path=audit_path,
        max_daily_loss_usd=50.0,
        budget_tracker=budget_tracker,
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
    assert "max_daily_loss_exceeded" in event["checks"]["failures"]


@pytest.mark.asyncio
async def test_executor_max_notional_blocks_when_exceeded(tmp_path: Path) -> None:
    """Test that max notional cap blocks orders when limit would be exceeded."""
    from unittest.mock import AsyncMock

    audit_path = tmp_path / "trade_audit.jsonl"

    client = AsyncMock()
    client.create_order = AsyncMock()

    budget_tracker = AsyncMock()
    budget_tracker.get_daily_loss_usd = AsyncMock(return_value=0.0)
    budget_tracker.get_daily_spend_usd = AsyncMock(return_value=195.0)

    executor = TradeExecutor(
        client,
        live=True,
        environment=Environment.DEMO,
        require_confirmation=False,
        audit_log_path=audit_path,
        max_notional_usd=200.0,
        budget_tracker=budget_tracker,
    )

    # This order would risk ~$55, exceeding $200 total (195 + 55 = 250)
    with pytest.raises(TradeSafetyError):
        await executor.create_order(
            ticker="TEST-TICKER",
            side="yes",
            action="buy",
            count=100,
            yes_price_cents=55,
        )

    client.create_order.assert_not_awaited()
    event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[-1])
    assert "max_notional_exceeded" in event["checks"]["failures"]


@pytest.mark.asyncio
async def test_executor_position_cap_blocks_when_exceeded(tmp_path: Path) -> None:
    """Test that position cap blocks orders that would exceed max contracts."""
    from unittest.mock import AsyncMock

    audit_path = tmp_path / "trade_audit.jsonl"

    client = AsyncMock()
    client.create_order = AsyncMock()

    position_provider = AsyncMock()
    position_provider.get_position_quantity = AsyncMock(return_value=95)

    executor = TradeExecutor(
        client,
        live=True,
        environment=Environment.DEMO,
        require_confirmation=False,
        audit_log_path=audit_path,
        max_position_contracts=100,
        position_provider=position_provider,
    )

    # Current position: 95, trying to buy 10 more => 105 > 100
    with pytest.raises(TradeSafetyError):
        await executor.create_order(
            ticker="TEST-TICKER",
            side="yes",
            action="buy",
            count=10,
            yes_price_cents=55,
        )

    client.create_order.assert_not_awaited()
    event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[-1])
    assert "max_position_contracts_exceeded" in event["checks"]["failures"]


@pytest.mark.asyncio
async def test_executor_slippage_limit_blocks_when_exceeded(tmp_path: Path) -> None:
    """Test that slippage limit blocks orders with excessive slippage."""
    from unittest.mock import AsyncMock

    from kalshi_research.api.models.orderbook import Orderbook

    audit_path = tmp_path / "trade_audit.jsonl"

    client = AsyncMock()
    client.create_order = AsyncMock()

    # Mock orderbook with thin liquidity (small quantities)
    orderbook_provider = AsyncMock()
    orderbook = Orderbook(
        yes=[(50, 5)],  # Only 5 contracts available
        no=[(50, 5)],
    )
    orderbook_provider.get_orderbook = AsyncMock(return_value=orderbook)

    executor = TradeExecutor(
        client,
        live=True,
        environment=Environment.DEMO,
        require_confirmation=False,
        audit_log_path=audit_path,
        max_slippage_pct=5.0,
        orderbook_provider=orderbook_provider,
    )

    # Try to buy 100 contracts (way more than available)
    with pytest.raises(TradeSafetyError):
        await executor.create_order(
            ticker="TEST-TICKER",
            side="yes",
            action="buy",
            count=100,
            yes_price_cents=50,
        )

    client.create_order.assert_not_awaited()
    event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[-1])
    assert "slippage_limit_exceeded" in event["checks"]["failures"]


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_executor_cancel_order_respects_kill_switch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that cancel_order wrapper respects the kill switch."""
    audit_path = tmp_path / "trade_audit.jsonl"

    monkeypatch.setenv("KALSHI_TRADE_KILL_SWITCH", "1")

    client = AsyncMock()
    client.cancel_order = AsyncMock()

    executor = TradeExecutor(
        client,
        live=True,
        environment=Environment.DEMO,
        require_confirmation=False,
        audit_log_path=audit_path,
    )

    with pytest.raises(TradeSafetyError) as exc_info:
        await executor.cancel_order("order-123")

    assert "kill_switch_enabled" in str(exc_info.value)
    client.cancel_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_executor_amend_order_respects_production_gate(tmp_path: Path) -> None:
    """Test that amend_order wrapper respects production gating."""
    audit_path = tmp_path / "trade_audit.jsonl"

    client = AsyncMock()
    client.amend_order = AsyncMock()

    executor = TradeExecutor(
        client,
        live=True,
        environment=Environment.PRODUCTION,
        allow_production=False,
        require_confirmation=False,
        audit_log_path=audit_path,
    )

    with pytest.raises(TradeSafetyError) as exc_info:
        await executor.amend_order(
            order_id="order-123",
            ticker="TEST-TICKER",
            side="yes",
            action="buy",
            client_order_id="client-123",
            updated_client_order_id="client-124",
            price=55,
        )

    assert "production_trading_disabled" in str(exc_info.value)
    client.amend_order.assert_not_awaited()


# DEBT-039: Exception handling tests


@pytest.mark.asyncio
async def test_executor_orderbook_provider_api_error_blocks_trade(tmp_path: Path) -> None:
    """Test that KalshiAPIError from orderbook provider blocks the trade (fail closed)."""
    from kalshi_research.api.exceptions import KalshiAPIError

    audit_path = tmp_path / "trade_audit.jsonl"

    client = AsyncMock()
    client.create_order = AsyncMock()

    orderbook_provider = AsyncMock()
    orderbook_provider.get_orderbook = AsyncMock(
        side_effect=KalshiAPIError(500, "Internal server error")
    )

    executor = TradeExecutor(
        client,
        live=True,
        environment=Environment.DEMO,
        require_confirmation=False,
        audit_log_path=audit_path,
        orderbook_provider=orderbook_provider,
    )

    with pytest.raises(TradeSafetyError):
        await executor.create_order(
            ticker="TEST-TICKER",
            side="yes",
            action="buy",
            count=1,
            yes_price_cents=50,
        )

    client.create_order.assert_not_awaited()
    event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[-1])
    assert "orderbook_provider_failed" in event["checks"]["failures"]


@pytest.mark.asyncio
async def test_executor_orderbook_provider_network_error_blocks_trade(tmp_path: Path) -> None:
    """Test that httpx.HTTPError from orderbook provider blocks the trade (fail closed)."""
    import httpx

    audit_path = tmp_path / "trade_audit.jsonl"

    client = AsyncMock()
    client.create_order = AsyncMock()

    orderbook_provider = AsyncMock()
    orderbook_provider.get_orderbook = AsyncMock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    executor = TradeExecutor(
        client,
        live=True,
        environment=Environment.DEMO,
        require_confirmation=False,
        audit_log_path=audit_path,
        orderbook_provider=orderbook_provider,
    )

    with pytest.raises(TradeSafetyError):
        await executor.create_order(
            ticker="TEST-TICKER",
            side="yes",
            action="buy",
            count=1,
            yes_price_cents=50,
        )

    client.create_order.assert_not_awaited()
    event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[-1])
    assert "orderbook_provider_failed" in event["checks"]["failures"]


@pytest.mark.asyncio
async def test_executor_orderbook_provider_timeout_blocks_trade(tmp_path: Path) -> None:
    """Test that httpx.TimeoutException from orderbook provider blocks the trade."""
    import httpx

    audit_path = tmp_path / "trade_audit.jsonl"

    client = AsyncMock()
    client.create_order = AsyncMock()

    orderbook_provider = AsyncMock()
    orderbook_provider.get_orderbook = AsyncMock(side_effect=httpx.ReadTimeout("Timeout"))

    executor = TradeExecutor(
        client,
        live=True,
        environment=Environment.DEMO,
        require_confirmation=False,
        audit_log_path=audit_path,
        orderbook_provider=orderbook_provider,
    )

    with pytest.raises(TradeSafetyError):
        await executor.create_order(
            ticker="TEST-TICKER",
            side="yes",
            action="buy",
            count=1,
            yes_price_cents=50,
        )

    client.create_order.assert_not_awaited()
    event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[-1])
    assert "orderbook_provider_failed" in event["checks"]["failures"]


@pytest.mark.asyncio
async def test_executor_liquidity_check_api_error_blocks_trade(tmp_path: Path) -> None:
    """Test that KalshiAPIError from market provider blocks the trade (fail closed)."""
    from kalshi_research.analysis.liquidity import LiquidityGrade
    from kalshi_research.api.exceptions import KalshiAPIError
    from kalshi_research.api.models.orderbook import Orderbook

    audit_path = tmp_path / "trade_audit.jsonl"

    client = AsyncMock()
    client.create_order = AsyncMock()

    # Orderbook provider works fine
    orderbook_provider = AsyncMock()
    orderbook = Orderbook(yes=[(50, 100)], no=[(50, 100)])
    orderbook_provider.get_orderbook = AsyncMock(return_value=orderbook)

    # Market provider fails
    market_provider = AsyncMock()
    market_provider.get_market = AsyncMock(side_effect=KalshiAPIError(404, "Market not found"))

    executor = TradeExecutor(
        client,
        live=True,
        environment=Environment.DEMO,
        require_confirmation=False,
        audit_log_path=audit_path,
        orderbook_provider=orderbook_provider,
        market_provider=market_provider,
        min_liquidity_grade=LiquidityGrade.MODERATE,
    )

    with pytest.raises(TradeSafetyError):
        await executor.create_order(
            ticker="TEST-TICKER",
            side="yes",
            action="buy",
            count=1,
            yes_price_cents=50,
        )

    client.create_order.assert_not_awaited()
    event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[-1])
    assert "liquidity_check_failed" in event["checks"]["failures"]


@pytest.mark.asyncio
async def test_executor_liquidity_check_timeout_blocks_trade(tmp_path: Path) -> None:
    """Test that httpx.TimeoutException from market provider blocks the trade."""
    import httpx

    from kalshi_research.analysis.liquidity import LiquidityGrade
    from kalshi_research.api.models.orderbook import Orderbook

    audit_path = tmp_path / "trade_audit.jsonl"

    client = AsyncMock()
    client.create_order = AsyncMock()

    # Orderbook provider works fine
    orderbook_provider = AsyncMock()
    orderbook = Orderbook(yes=[(50, 100)], no=[(50, 100)])
    orderbook_provider.get_orderbook = AsyncMock(return_value=orderbook)

    # Market provider times out
    market_provider = AsyncMock()
    market_provider.get_market = AsyncMock(side_effect=httpx.ReadTimeout("Timeout"))

    executor = TradeExecutor(
        client,
        live=True,
        environment=Environment.DEMO,
        require_confirmation=False,
        audit_log_path=audit_path,
        orderbook_provider=orderbook_provider,
        market_provider=market_provider,
        min_liquidity_grade=LiquidityGrade.MODERATE,
    )

    with pytest.raises(TradeSafetyError):
        await executor.create_order(
            ticker="TEST-TICKER",
            side="yes",
            action="buy",
            count=1,
            yes_price_cents=50,
        )

    client.create_order.assert_not_awaited()
    event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[-1])
    assert "liquidity_check_failed" in event["checks"]["failures"]
