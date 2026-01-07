"""Alert conditions and alert definitions."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ConditionType(str, Enum):
    """Types of alert conditions."""

    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PRICE_CROSSES = "price_crosses"
    SPREAD_ABOVE = "spread_above"
    VOLUME_ABOVE = "volume_above"
    EDGE_DETECTED = "edge_detected"


class AlertStatus(str, Enum):
    """Alert lifecycle status."""

    PENDING = "pending"
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    EXPIRED = "expired"
    CLEARED = "cleared"


@dataclass
class AlertCondition:
    """
    Defines a condition to monitor.

    Attributes:
        id: Unique identifier for this condition
        condition_type: Type of condition to check
        ticker: Market ticker to monitor (or "*" for all markets)
        threshold: Numeric threshold value
        label: Human-readable description
        expires_at: Optional expiration time
        created_at: When the condition was created
    """

    id: str
    condition_type: ConditionType
    ticker: str
    threshold: float
    label: str
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def is_expired(self) -> bool:
        """Check if this condition has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at


@dataclass
class Alert:
    """
    A triggered alert.

    Attributes:
        id: Unique alert ID
        condition: The condition that triggered this alert
        triggered_at: When the alert was triggered
        status: Current status
        current_value: The value that triggered the alert
        market_data: Additional market context
    """

    id: str
    condition: AlertCondition
    triggered_at: datetime
    status: AlertStatus
    current_value: float
    market_data: dict[str, Any] = field(default_factory=dict)

    def acknowledge(self) -> None:
        """Mark alert as acknowledged."""
        self.status = AlertStatus.ACKNOWLEDGED

    def clear(self) -> None:
        """Clear the alert."""
        self.status = AlertStatus.CLEARED
