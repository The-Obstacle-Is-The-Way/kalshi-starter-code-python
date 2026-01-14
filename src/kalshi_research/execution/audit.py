"""JSONL audit logging for trade execution attempts."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from kalshi_research.execution.models import TradeAuditEvent


class TradeAuditLogger:
    """Append-only JSONL logger for trade attempts."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        """Return the JSONL audit log path."""
        return self._path

    def write(self, event: TradeAuditEvent) -> None:
        """Append one audit event as a single JSONL line."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = event.model_dump(mode="json")
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
