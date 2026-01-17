"""Tests for alert monitor."""

from datetime import UTC, datetime, timedelta

import pytest

from kalshi_research.alerts.conditions import (
    Alert,
    AlertCondition,
    AlertStatus,
    ConditionType,
)
from kalshi_research.alerts.monitor import AlertMonitor
from kalshi_research.api.models.market import Market, MarketStatus


def make_market(
    ticker: str,
    yes_price: int = 50,
    yes_bid: int | None = None,
    yes_ask: int | None = None,
    volume: int = 10000,
    volume_24h: int = 5000,
) -> Market:
    """Helper to create test markets."""
    if yes_bid is None:
        yes_bid = yes_price - 2
    if yes_ask is None:
        yes_ask = yes_price + 2

    no_bid = 100 - yes_ask
    no_ask = 100 - yes_bid

    return Market(
        ticker=ticker,
        event_ticker="EVENT-1",
        title=f"Test Market {ticker}",
        status=MarketStatus.ACTIVE,
        yes_bid=yes_bid,
        yes_ask=yes_ask,
        yes_bid_dollars=f"{yes_bid / 100:.4f}",
        yes_ask_dollars=f"{yes_ask / 100:.4f}",
        no_bid=no_bid,
        no_ask=no_ask,
        no_bid_dollars=f"{no_bid / 100:.4f}",
        no_ask_dollars=f"{no_ask / 100:.4f}",
        volume=volume,
        volume_24h=volume_24h,
        open_interest=1000,
        open_time=datetime.now(UTC) - timedelta(days=1),
        close_time=datetime.now(UTC) + timedelta(days=30),
        expiration_time=datetime.now(UTC) + timedelta(days=30),
        liquidity=50000,
    )


class TestAlertMonitor:
    """Test AlertMonitor class."""

    def test_add_and_list_conditions(self) -> None:
        """Test adding and listing conditions."""
        monitor = AlertMonitor()

        condition1 = AlertCondition(
            id="cond-1",
            condition_type=ConditionType.PRICE_ABOVE,
            ticker="KXBTC-25JAN-T100000",
            threshold=0.75,
            label="BTC bullish",
        )
        condition2 = AlertCondition(
            id="cond-2",
            condition_type=ConditionType.VOLUME_ABOVE,
            ticker="INXU-25JAN-B200",
            threshold=5000.0,
            label="High volume",
        )

        monitor.add_condition(condition1)
        monitor.add_condition(condition2)

        conditions = monitor.list_conditions()
        assert len(conditions) == 2
        assert condition1 in conditions
        assert condition2 in conditions

    def test_remove_condition(self) -> None:
        """Test removing a condition."""
        monitor = AlertMonitor()

        condition = AlertCondition(
            id="cond-1",
            condition_type=ConditionType.PRICE_ABOVE,
            ticker="TEST",
            threshold=0.5,
            label="Test",
        )

        monitor.add_condition(condition)
        assert len(monitor.list_conditions()) == 1

        removed = monitor.remove_condition("cond-1")
        assert removed is True
        assert len(monitor.list_conditions()) == 0

        # Removing non-existent condition returns False
        removed = monitor.remove_condition("non-existent")
        assert removed is False

    @pytest.mark.asyncio
    async def test_check_price_above_triggers(self) -> None:
        """Test PRICE_ABOVE condition triggers when threshold exceeded."""
        monitor = AlertMonitor()

        condition = AlertCondition(
            id="price-test",
            condition_type=ConditionType.PRICE_ABOVE,
            ticker="KXBTC-25JAN-T100000",
            threshold=0.75,
            label="BTC > 75%",
        )
        monitor.add_condition(condition)

        # Market with yes_price = 80 (0.80 as decimal)
        market = make_market(ticker="KXBTC-25JAN-T100000", yes_price=80)

        alerts = await monitor.check_conditions([market])

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.condition.id == "price-test"
        assert alert.status == AlertStatus.TRIGGERED
        assert alert.current_value == 0.80
        assert alert.market_data["ticker"] == "KXBTC-25JAN-T100000"

    @pytest.mark.asyncio
    async def test_check_price_above_no_trigger(self) -> None:
        """Test PRICE_ABOVE condition doesn't trigger when below threshold."""
        monitor = AlertMonitor()

        condition = AlertCondition(
            id="price-test",
            condition_type=ConditionType.PRICE_ABOVE,
            ticker="KXBTC-25JAN-T100000",
            threshold=0.75,
            label="BTC > 75%",
        )
        monitor.add_condition(condition)

        # Market with yes_price = 70 (0.70 as decimal) - below threshold
        market = make_market(ticker="KXBTC-25JAN-T100000", yes_price=70)

        alerts = await monitor.check_conditions([market])
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_check_conditions_skips_markets_with_missing_midpoint(self) -> None:
        monitor = AlertMonitor()

        condition = AlertCondition(
            id="price-test",
            condition_type=ConditionType.PRICE_ABOVE,
            ticker="MISSING",
            threshold=0.50,
            label="Missing midpoint",
        )
        monitor.add_condition(condition)

        market = make_market(ticker="MISSING", yes_price=60).model_copy(
            update={"yes_bid_dollars": None, "yes_ask_dollars": None}
        )

        alerts = await monitor.check_conditions([market])

        assert alerts == []
        assert len(monitor.list_conditions()) == 1

    @pytest.mark.asyncio
    async def test_check_price_below_triggers(self) -> None:
        """Test PRICE_BELOW condition triggers when threshold exceeded."""
        monitor = AlertMonitor()

        condition = AlertCondition(
            id="price-test",
            condition_type=ConditionType.PRICE_BELOW,
            ticker="INXU-25JAN-B200",
            threshold=0.30,
            label="S&P < 30%",
        )
        monitor.add_condition(condition)

        # Market with yes_price = 25 (0.25 as decimal)
        market = make_market(ticker="INXU-25JAN-B200", yes_price=25)

        alerts = await monitor.check_conditions([market])

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.condition.id == "price-test"
        assert alert.current_value == 0.25

    @pytest.mark.asyncio
    async def test_check_spread_above_triggers(self) -> None:
        """Test SPREAD_ABOVE condition triggers when spread exceeds threshold."""
        monitor = AlertMonitor()

        condition = AlertCondition(
            id="spread-test",
            condition_type=ConditionType.SPREAD_ABOVE,
            ticker="TEST-TICKER",
            threshold=5.0,
            label="Wide spread",
        )
        monitor.add_condition(condition)

        # Market with spread = 10 (ask 60 - bid 50)
        market = make_market(ticker="TEST-TICKER", yes_bid=50, yes_ask=60)

        alerts = await monitor.check_conditions([market])

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.condition.id == "spread-test"
        assert alert.current_value == 10.0

    @pytest.mark.asyncio
    async def test_check_volume_above_triggers(self) -> None:
        """Test VOLUME_ABOVE condition triggers when volume exceeds threshold."""
        monitor = AlertMonitor()

        condition = AlertCondition(
            id="volume-test",
            condition_type=ConditionType.VOLUME_ABOVE,
            ticker="TEST-TICKER",
            threshold=5000.0,
            label="High volume",
        )
        monitor.add_condition(condition)

        # Market with volume = 8000
        market = make_market(ticker="TEST-TICKER", volume=8000)

        alerts = await monitor.check_conditions([market])

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.condition.id == "volume-test"
        assert alert.current_value == 8000.0

    @pytest.mark.asyncio
    async def test_check_price_crosses_triggers_on_cross(self) -> None:
        """Test PRICE_CROSSES triggers only when the price crosses the threshold."""
        monitor = AlertMonitor()

        condition = AlertCondition(
            id="cross-test",
            condition_type=ConditionType.PRICE_CROSSES,
            ticker="TEST-CROSS",
            threshold=0.5,
            label="Crosses 50%",
        )
        monitor.add_condition(condition)

        # First observation establishes baseline; should not trigger.
        alerts = await monitor.check_conditions([make_market(ticker="TEST-CROSS", yes_price=40)])
        assert alerts == []
        assert len(monitor.list_conditions()) == 1

        # Cross upward over 50% should trigger.
        alerts = await monitor.check_conditions([make_market(ticker="TEST-CROSS", yes_price=60)])
        assert len(alerts) == 1
        assert alerts[0].condition.id == "cross-test"
        assert alerts[0].current_value == 0.60

    @pytest.mark.asyncio
    async def test_check_edge_detected_triggers_on_large_move(self) -> None:
        """Test EDGE_DETECTED triggers on large absolute moves since last check."""
        monitor = AlertMonitor()

        condition = AlertCondition(
            id="edge-test",
            condition_type=ConditionType.EDGE_DETECTED,
            ticker="TEST-EDGE",
            threshold=0.10,
            label="Move >= 10%",
        )
        monitor.add_condition(condition)

        # First observation establishes baseline; should not trigger.
        alerts = await monitor.check_conditions([make_market(ticker="TEST-EDGE", yes_price=50)])
        assert alerts == []
        assert len(monitor.list_conditions()) == 1

        # Move from 50% -> 65% is +15%, should trigger.
        alerts = await monitor.check_conditions([make_market(ticker="TEST-EDGE", yes_price=65)])
        assert len(alerts) == 1
        assert alerts[0].condition.id == "edge-test"
        assert alerts[0].current_value == pytest.approx(0.15)

    @pytest.mark.asyncio
    async def test_expired_conditions_removed(self) -> None:
        """Test that expired conditions are automatically removed."""
        monitor = AlertMonitor()

        # Add expired condition
        expired_condition = AlertCondition(
            id="expired",
            condition_type=ConditionType.PRICE_ABOVE,
            ticker="TEST",
            threshold=0.5,
            label="Expired",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        monitor.add_condition(expired_condition)

        # Add active condition
        active_condition = AlertCondition(
            id="active",
            condition_type=ConditionType.PRICE_ABOVE,
            ticker="TEST2",
            threshold=0.5,
            label="Active",
        )
        monitor.add_condition(active_condition)

        assert len(monitor.list_conditions()) == 2

        # Check conditions - expired should be removed
        market = make_market(ticker="TEST", yes_price=60)

        await monitor.check_conditions([market])

        # Only active condition should remain
        conditions = monitor.list_conditions()
        assert len(conditions) == 1
        assert conditions[0].id == "active"

    @pytest.mark.asyncio
    async def test_condition_removed_after_trigger(self) -> None:
        """Test that conditions are removed after triggering (one-shot)."""
        monitor = AlertMonitor()

        condition = AlertCondition(
            id="one-shot",
            condition_type=ConditionType.PRICE_ABOVE,
            ticker="TEST",
            threshold=0.5,
            label="One-shot alert",
        )
        monitor.add_condition(condition)

        market = make_market(ticker="TEST", yes_price=60)

        alerts = await monitor.check_conditions([market])
        assert len(alerts) == 1

        # Condition should be removed after triggering
        assert len(monitor.list_conditions()) == 0

    @pytest.mark.asyncio
    async def test_notifiers_called_on_trigger(self) -> None:
        """Test that notifiers are called when alert triggers."""
        monitor = AlertMonitor()

        # Track notifications
        notifications: list[Alert] = []

        class TestNotifier:
            def notify(self, alert: Alert) -> None:
                notifications.append(alert)

        monitor.add_notifier(TestNotifier())

        condition = AlertCondition(
            id="notify-test",
            condition_type=ConditionType.PRICE_ABOVE,
            ticker="TEST",
            threshold=0.5,
            label="Test notify",
        )
        monitor.add_condition(condition)

        market = make_market(ticker="TEST", yes_price=60)

        await monitor.check_conditions([market])

        # Notifier should have been called
        assert len(notifications) == 1
        assert notifications[0].condition.id == "notify-test"

    @pytest.mark.asyncio
    async def test_missing_ticker_no_alert(self) -> None:
        """Test that no alert is triggered if market ticker is not found."""
        monitor = AlertMonitor()

        condition = AlertCondition(
            id="missing-ticker",
            condition_type=ConditionType.PRICE_ABOVE,
            ticker="NON-EXISTENT",
            threshold=0.5,
            label="Missing ticker",
        )
        monitor.add_condition(condition)

        # Market with different ticker
        market = make_market(ticker="DIFFERENT-TICKER", yes_price=60)

        alerts = await monitor.check_conditions([market])
        assert len(alerts) == 0

        # Condition should still exist (not triggered)
        assert len(monitor.list_conditions()) == 1

    @pytest.mark.asyncio
    async def test_sentiment_shift_triggers(self) -> None:
        monitor = AlertMonitor()

        condition = AlertCondition(
            id="sentiment-test",
            condition_type=ConditionType.SENTIMENT_SHIFT,
            ticker="TEST-SENT",
            threshold=0.2,
            label="Sentiment shift",
        )
        monitor.add_condition(condition)

        market = make_market(ticker="TEST-SENT", yes_price=50)
        alerts = await monitor.check_conditions(
            [market],
            sentiment_shift_by_ticker={"TEST-SENT": 0.25},
        )

        assert len(alerts) == 1
        assert alerts[0].condition.id == "sentiment-test"
        assert alerts[0].current_value == 0.25

    def test_list_alerts(self) -> None:
        """Test listing triggered alerts."""
        monitor = AlertMonitor()

        # Manually add a triggered alert to internal list
        condition = AlertCondition(
            id="test",
            condition_type=ConditionType.PRICE_ABOVE,
            ticker="TEST",
            threshold=0.5,
            label="Test",
        )

        alert = Alert(
            id="alert-1",
            condition=condition,
            triggered_at=datetime.now(UTC),
            status=AlertStatus.TRIGGERED,
            current_value=0.6,
        )

        monitor._triggered_alerts.append(alert)

        alerts = monitor.list_alerts()
        assert len(alerts) == 1
        assert alerts[0].id == "alert-1"
