"""Scanner models and types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class MarketClosedError(Exception):
    """Raised when attempting to operate on a closed market."""

    pass


class ScanFilter(str, Enum):
    """Types of market scans."""

    CLOSE_RACE = "close_race"  # Markets near 50%
    HIGH_VOLUME = "high_volume"  # High trading activity
    WIDE_SPREAD = "wide_spread"  # Wide bid-ask spread
    EXPIRING_SOON = "expiring_soon"  # Close to expiration
    PRICE_MOVER = "price_mover"  # Recent large moves


@dataclass
class ScanResult:
    """Result from a market scan."""

    ticker: str
    title: str
    filter_type: ScanFilter
    score: float  # 0-1 relevance score
    market_prob: float
    volume_24h: int
    spread: int

    details: dict[str, object] = field(default_factory=dict)
    scanned_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __str__(self) -> str:
        return (
            f"[{self.filter_type.value.upper()}] {self.ticker}\n"
            f"  {self.title[:50]}...\n"
            f"  Prob: {self.market_prob:.0%} | Vol: {self.volume_24h:,} | Spread: {self.spread}c"
        )
