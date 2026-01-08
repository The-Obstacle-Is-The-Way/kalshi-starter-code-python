"""Centralized path defaults for Kalshi Research Platform."""

from pathlib import Path

DEFAULT_DATA_DIR = Path("data")
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "kalshi.db"
DEFAULT_ALERTS_PATH = DEFAULT_DATA_DIR / "alerts.json"
DEFAULT_THESES_PATH = DEFAULT_DATA_DIR / "theses.json"
DEFAULT_EXPORTS_DIR = DEFAULT_DATA_DIR / "exports"
DEFAULT_ALERT_LOG = DEFAULT_DATA_DIR / "alert_monitor.log"
