"""Tests for alert conditions and alerts."""

from datetime import UTC, datetime, timedelta

from kalshi_research.alerts.conditions import (
    Alert,
    AlertCondition,
    AlertStatus,
    ConditionType,
)


class TestAlertCondition:
    """Test AlertCondition dataclass."""

    def test_create_basic_condition(self) -> None:
        """Test creating a basic alert condition."""
        condition = AlertCondition(
            id="test-1",
            condition_type=ConditionType.PRICE_ABOVE,
            ticker="KXBTC-25JAN-T100000",
            threshold=0.75,
            label="BTC >$100k hitting 75%",
        )

        assert condition.id == "test-1"
        assert condition.condition_type == ConditionType.PRICE_ABOVE
        assert condition.ticker == "KXBTC-25JAN-T100000"
        assert condition.threshold == 0.75
        assert condition.label == "BTC >$100k hitting 75%"
        assert condition.expires_at is None
        assert condition.created_at is not None

    def test_condition_with_expiration(self) -> None:
        """Test condition with expiration time."""
        expires = datetime.now(UTC) + timedelta(hours=1)
        condition = AlertCondition(
            id="test-2",
            condition_type=ConditionType.PRICE_BELOW,
            ticker="INXU-25JAN-B200",
            threshold=0.30,
            label="S&P bearish",
            expires_at=expires,
        )

        assert condition.expires_at == expires
        assert not condition.is_expired()

    def test_is_expired_when_no_expiration(self) -> None:
        """Test that condition never expires when expires_at is None."""
        condition = AlertCondition(
            id="test-3",
            condition_type=ConditionType.VOLUME_ABOVE,
            ticker="TEST-TICKER",
            threshold=1000.0,
            label="High volume",
        )

        assert not condition.is_expired()

    def test_is_expired_when_expired(self) -> None:
        """Test that condition is expired after expiration time."""
        expires = datetime.now(UTC) - timedelta(hours=1)
        condition = AlertCondition(
            id="test-4",
            condition_type=ConditionType.SPREAD_ABOVE,
            ticker="TEST-TICKER",
            threshold=5.0,
            label="Wide spread",
            expires_at=expires,
        )

        assert condition.is_expired()


class TestAlert:
    """Test Alert dataclass."""

    def test_create_alert(self) -> None:
        """Test creating an alert."""
        condition = AlertCondition(
            id="cond-1",
            condition_type=ConditionType.PRICE_ABOVE,
            ticker="KXBTC-25JAN-T100000",
            threshold=0.75,
            label="BTC bullish",
        )

        triggered_at = datetime.now(UTC)
        alert = Alert(
            id="alert-1",
            condition=condition,
            triggered_at=triggered_at,
            status=AlertStatus.TRIGGERED,
            current_value=0.78,
            market_data={
                "ticker": "KXBTC-25JAN-T100000",
                "title": "BTC >$100k by Jan 25",
                "yes_price": 78,
                "volume": 5000,
            },
        )

        assert alert.id == "alert-1"
        assert alert.condition == condition
        assert alert.triggered_at == triggered_at
        assert alert.status == AlertStatus.TRIGGERED
        assert alert.current_value == 0.78
        assert alert.market_data["ticker"] == "KXBTC-25JAN-T100000"

    def test_acknowledge_alert(self) -> None:
        """Test acknowledging an alert."""
        condition = AlertCondition(
            id="cond-1",
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

        assert alert.status == AlertStatus.TRIGGERED
        alert.acknowledge()
        assert alert.status == AlertStatus.ACKNOWLEDGED

    def test_clear_alert(self) -> None:
        """Test clearing an alert."""
        condition = AlertCondition(
            id="cond-1",
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

        assert alert.status == AlertStatus.TRIGGERED
        alert.clear()
        assert alert.status == AlertStatus.CLEARED


class TestConditionType:
    """Test ConditionType enum."""

    def test_all_condition_types(self) -> None:
        """Test all condition types are defined."""
        assert ConditionType.PRICE_ABOVE.value == "price_above"
        assert ConditionType.PRICE_BELOW.value == "price_below"
        assert ConditionType.PRICE_CROSSES.value == "price_crosses"
        assert ConditionType.SPREAD_ABOVE.value == "spread_above"
        assert ConditionType.VOLUME_ABOVE.value == "volume_above"
        assert ConditionType.EDGE_DETECTED.value == "edge_detected"


class TestAlertStatus:
    """Test AlertStatus enum."""

    def test_all_statuses(self) -> None:
        """Test all alert statuses are defined."""
        assert AlertStatus.PENDING.value == "pending"
        assert AlertStatus.TRIGGERED.value == "triggered"
        assert AlertStatus.ACKNOWLEDGED.value == "acknowledged"
        assert AlertStatus.EXPIRED.value == "expired"
        assert AlertStatus.CLEARED.value == "cleared"
