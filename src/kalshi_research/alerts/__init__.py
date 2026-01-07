"""
Kalshi Research Platform - Alerts Module.

This module provides alerting and notification capabilities for monitoring
Kalshi prediction markets. It supports various condition types (price thresholds,
spread changes, volume spikes) and multiple notification channels (console, file, webhook).
"""

from kalshi_research.alerts.conditions import (
    Alert,
    AlertCondition,
    AlertStatus,
    ConditionType,
)
from kalshi_research.alerts.monitor import AlertMonitor

__all__ = [
    "Alert",
    "AlertCondition",
    "AlertMonitor",
    "AlertStatus",
    "ConditionType",
]
