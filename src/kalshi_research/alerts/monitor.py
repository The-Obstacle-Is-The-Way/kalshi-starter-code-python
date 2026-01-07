"""Alert monitoring and condition checking."""

import uuid
from datetime import UTC, datetime
from typing import Protocol

from kalshi_research.alerts.conditions import (
    Alert,
    AlertCondition,
    AlertStatus,
    ConditionType,
)
from kalshi_research.api.models import Market


class Notifier(Protocol):
    """Protocol for notification channels."""

    def notify(self, alert: Alert) -> None:
        """Send notification for an alert."""
        ...


class AlertMonitor:
    """
    Monitor markets against defined conditions.

    Usage:
        monitor = AlertMonitor()
        monitor.add_notifier(ConsoleNotifier())
        monitor.add_condition(AlertCondition(...))

        # In your polling loop:
        alerts = await monitor.check_conditions(markets)
    """

    def __init__(self) -> None:
        self._conditions: dict[str, AlertCondition] = {}
        self._notifiers: list[Notifier] = []
        self._triggered_alerts: list[Alert] = []

    def add_condition(self, condition: AlertCondition) -> None:
        """Add a condition to monitor."""
        self._conditions[condition.id] = condition

    def remove_condition(self, condition_id: str) -> bool:
        """Remove a condition by ID. Returns True if found."""
        return self._conditions.pop(condition_id, None) is not None

    def add_notifier(self, notifier: Notifier) -> None:
        """Add a notification channel."""
        self._notifiers.append(notifier)

    def list_conditions(self) -> list[AlertCondition]:
        """List all active conditions."""
        return list(self._conditions.values())

    def list_alerts(self) -> list[Alert]:
        """List all triggered alerts."""
        return self._triggered_alerts.copy()

    async def check_conditions(
        self,
        markets: list[Market],
    ) -> list[Alert]:
        """
        Check all conditions against current market data.

        Args:
            markets: List of current market data

        Returns:
            List of newly triggered alerts
        """
        new_alerts: list[Alert] = []
        market_lookup = {m.ticker: m for m in markets}

        for condition in list(self._conditions.values()):
            # Skip expired conditions
            if condition.is_expired():
                del self._conditions[condition.id]
                continue

            # Check if condition matches
            alert = self._check_condition(condition, market_lookup)
            if alert:
                new_alerts.append(alert)
                self._triggered_alerts.append(alert)

                # Notify all channels
                for notifier in self._notifiers:
                    notifier.notify(alert)

                # Remove one-shot conditions after triggering
                del self._conditions[condition.id]

        return new_alerts

    def _check_condition(
        self,
        condition: AlertCondition,
        markets: dict[str, Market],
    ) -> Alert | None:
        """Check a single condition against market data."""
        market = markets.get(condition.ticker)
        if market is None:
            return None

        triggered = False
        current_value = 0.0

        match condition.condition_type:
            case ConditionType.PRICE_ABOVE:
                # Calculate mid price from bid/ask
                mid_price = (market.yes_bid + market.yes_ask) / 2.0
                current_value = mid_price / 100.0
                triggered = current_value > condition.threshold

            case ConditionType.PRICE_BELOW:
                # Calculate mid price from bid/ask
                mid_price = (market.yes_bid + market.yes_ask) / 2.0
                current_value = mid_price / 100.0
                triggered = current_value < condition.threshold

            case ConditionType.SPREAD_ABOVE:
                spread = market.yes_ask - market.yes_bid
                current_value = float(spread)
                triggered = current_value > condition.threshold

            case ConditionType.VOLUME_ABOVE:
                current_value = float(market.volume)
                triggered = current_value > condition.threshold

        if triggered:
            return Alert(
                id=str(uuid.uuid4()),
                condition=condition,
                triggered_at=datetime.now(UTC),
                status=AlertStatus.TRIGGERED,
                current_value=current_value,
                market_data={
                    "ticker": market.ticker,
                    "title": market.title,
                    "yes_bid": market.yes_bid,
                    "yes_ask": market.yes_ask,
                    "volume": market.volume,
                },
            )

        return None
