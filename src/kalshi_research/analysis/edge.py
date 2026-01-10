"""Edge detection for prediction market research."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class EdgeType(str, Enum):
    """Types of trading edges."""

    THESIS = "thesis"  # Your view differs from market
    VOLATILITY = "volatility"  # Unusual price movement
    SPREAD = "spread"  # Wide spread opportunity
    VOLUME = "volume"  # Volume spike
    CORRELATION = "correlation"  # Related market inconsistency


@dataclass
class Edge:
    """Represents a potential trading edge."""

    ticker: str
    edge_type: EdgeType
    confidence: float  # 0-1 confidence in edge
    market_price: float  # Current market probability
    your_estimate: float | None  # Your probability estimate
    expected_value: float | None  # Expected profit per contract (cents)

    description: str
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Supporting data
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        yours = f"{self.your_estimate:.0%}" if self.your_estimate is not None else "N/A"
        ev = f"{self.expected_value:+.1f}c" if self.expected_value is not None else "N/A"
        return (
            f"[{self.edge_type.value.upper()}] {self.ticker}\n"
            f"  Market: {self.market_price:.0%} | Yours: {yours} | EV: {ev}\n"
            f"  {self.description}"
        )
