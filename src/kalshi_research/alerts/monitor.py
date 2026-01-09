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
        self._last_mid_probs: dict[str, float] = {}

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
        *,
        sentiment_shift_by_ticker: dict[str, float] | None = None,
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
        current_mid_probs: dict[str, float] = {}
        shift_lookup = sentiment_shift_by_ticker or {}

        for condition in list(self._conditions.values()):
            # Skip expired conditions
            if condition.is_expired():
                del self._conditions[condition.id]
                continue

            # Check if condition matches
            market = market_lookup.get(condition.ticker)
            if market is None:
                continue

            mid_prob = market.midpoint / 100.0
            current_mid_probs[condition.ticker] = mid_prob
            alert = self._check_condition(
                condition,
                market,
                mid_prob=mid_prob,
                prev_mid_prob=self._last_mid_probs.get(condition.ticker),
                sentiment_shift=shift_lookup.get(condition.ticker),
            )
            if alert:
                new_alerts.append(alert)
                self._triggered_alerts.append(alert)

                # Notify all channels
                for notifier in self._notifiers:
                    notifier.notify(alert)

                # Remove one-shot conditions after triggering
                del self._conditions[condition.id]

        self._last_mid_probs.update(current_mid_probs)
        return new_alerts

    def _check_condition(
        self,
        condition: AlertCondition,
        market: Market,
        *,
        mid_prob: float,
        prev_mid_prob: float | None,
        sentiment_shift: float | None,
    ) -> Alert | None:
        """Check a single condition against market data."""
        triggered = False
        current_value = 0.0

        match condition.condition_type:
            case ConditionType.PRICE_ABOVE:
                # Calculate mid price from bid/ask
                current_value = mid_prob
                triggered = current_value > condition.threshold

            case ConditionType.PRICE_BELOW:
                # Calculate mid price from bid/ask
                current_value = mid_prob
                triggered = current_value < condition.threshold

            case ConditionType.PRICE_CROSSES:
                # Triggers when the market moves from one side of the threshold to the other.
                current_value = mid_prob
                if prev_mid_prob is not None:
                    crossed_up = prev_mid_prob < condition.threshold <= current_value
                    crossed_down = prev_mid_prob > condition.threshold >= current_value
                    triggered = crossed_up or crossed_down

            case ConditionType.SPREAD_ABOVE:
                spread = market.spread
                current_value = float(spread)
                triggered = current_value > condition.threshold

            case ConditionType.VOLUME_ABOVE:
                current_value = float(market.volume)
                triggered = current_value > condition.threshold

            case ConditionType.EDGE_DETECTED:
                # Treat this as a volatility edge: trigger on large absolute moves since last check.
                if prev_mid_prob is not None and condition.threshold > 0:
                    current_value = abs(mid_prob - prev_mid_prob)
                    triggered = current_value >= condition.threshold

            case ConditionType.SENTIMENT_SHIFT:
                # Trigger on absolute change in rolling sentiment.
                # `sentiment_shift` is expected to be a delta (e.g., last 7d avg - previous 7d avg).
                if sentiment_shift is not None and condition.threshold > 0:
                    current_value = sentiment_shift
                    triggered = abs(sentiment_shift) >= condition.threshold

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
                    "yes_bid": market.yes_bid_cents,
                    "yes_ask": market.yes_ask_cents,
                    "volume": market.volume,
                },
            )

        return None
