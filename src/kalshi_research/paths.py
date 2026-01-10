"""
Centralized path defaults for Kalshi Research Platform.

All paths are expressed relative to the current working directory. CLI examples assume running
from the repository root, but every path default can be overridden via CLI options.
"""

from pathlib import Path

DEFAULT_DATA_DIR = Path("data")
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "kalshi.db"
DEFAULT_ALERTS_PATH = DEFAULT_DATA_DIR / "alerts.json"
DEFAULT_THESES_PATH = DEFAULT_DATA_DIR / "theses.json"
DEFAULT_EXPORTS_DIR = DEFAULT_DATA_DIR / "exports"
DEFAULT_ALERT_LOG = DEFAULT_DATA_DIR / "alert_monitor.log"
DEFAULT_TRADE_AUDIT_LOG = DEFAULT_DATA_DIR / "trade_audit.log"

__all__ = [
    "DEFAULT_ALERTS_PATH",
    "DEFAULT_ALERT_LOG",
    "DEFAULT_DATA_DIR",
    "DEFAULT_DB_PATH",
    "DEFAULT_EXPORTS_DIR",
    "DEFAULT_THESES_PATH",
    "DEFAULT_TRADE_AUDIT_LOG",
]
