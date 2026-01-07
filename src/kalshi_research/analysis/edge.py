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


class EdgeDetector:
    """
    Detect potential trading edges in market data.

    An "edge" exists when:
    1. Your probability estimate differs significantly from market price
    2. Historical patterns suggest mispricing
    3. Related markets show inconsistent pricing
    """

    def __init__(
        self,
        min_spread_cents: int = 5,
        min_volume_spike: float = 3.0,
        min_price_move: float = 0.10,
    ) -> None:
        """
        Initialize the detector.

        Args:
            min_spread_cents: Minimum spread to flag as wide
            min_volume_spike: Minimum volume multiple vs average
            min_price_move: Minimum price change to flag
        """
        self.min_spread_cents = min_spread_cents
        self.min_volume_spike = min_volume_spike
        self.min_price_move = min_price_move

    def detect_thesis_edge(
        self,
        ticker: str,
        market_prob: float,
        your_prob: float,
        min_edge: float = 0.05,
    ) -> Edge | None:
        """
        Detect edge when your estimate differs from market.

        Args:
            ticker: Market ticker
            market_prob: Current market probability (0-1)
            your_prob: Your probability estimate (0-1)
            min_edge: Minimum difference to flag (default 5%)

        Returns:
            Edge if detected, None otherwise
        """
        diff = your_prob - market_prob

        if abs(diff) < min_edge:
            return None

        if diff > 0:
            # Buy YES: Cost = market_prob * 100
            cost = market_prob * 100
            # If win (p=your_prob), profit = 100 - cost. If lose, loss = cost.
            ev = (your_prob * (100 - cost)) - ((1 - your_prob) * cost)
            side = "YES"
        else:
            # Buy NO: Cost = (1 - market_prob) * 100
            cost = (1 - market_prob) * 100
            ev = ((1 - your_prob) * (100 - cost)) - (your_prob * cost)
            side = "NO"

        return Edge(
            ticker=ticker,
            edge_type=EdgeType.THESIS,
            confidence=min(abs(diff) / 0.20, 1.0),  # Scale to 20% max
            market_price=market_prob,
            your_estimate=your_prob,
            expected_value=ev,
            description=f"Buy {side}: You estimate {your_prob:.0%} vs market {market_prob:.0%}",
            metadata={"side": side, "diff": diff},
        )

    def detect_spread_edge(
        self,
        ticker: str,
        bid: int,
        ask: int,
        typical_spread: int = 2,
    ) -> Edge | None:
        """
        Detect unusually wide spreads.

        Wide spreads might indicate:
        - Market making opportunity
        - Low liquidity / uncertainty
        - News pending

        Args:
            ticker: Market ticker
            bid: Best bid price (cents)
            ask: Best ask price (cents)
            typical_spread: Expected spread for this market

        Returns:
            Edge if detected, None otherwise
        """
        spread = ask - bid

        if spread <= self.min_spread_cents:
            return None

        return Edge(
            ticker=ticker,
            edge_type=EdgeType.SPREAD,
            confidence=min((spread - typical_spread) / 10, 1.0),
            market_price=(bid + ask) / 200.0,
            your_estimate=None,
            expected_value=float(spread / 2),  # Potential capture
            description=f"Wide spread: {spread}c (typical: {typical_spread}c)",
            metadata={"bid": bid, "ask": ask, "spread": spread},
        )

    def detect_volume_edge(
        self,
        ticker: str,
        current_volume: int,
        avg_volume: float,
        market_prob: float,
    ) -> Edge | None:
        """
        Detect unusual volume spikes.

        High volume might indicate:
        - New information entering market
        - Large trader activity
        - Imminent resolution

        Args:
            ticker: Market ticker
            current_volume: Recent volume
            avg_volume: Historical average volume
            market_prob: Current market probability

        Returns:
            Edge if detected, None otherwise
        """
        if avg_volume <= 0:
            return None

        volume_ratio = current_volume / avg_volume

        if volume_ratio < self.min_volume_spike:
            return None

        return Edge(
            ticker=ticker,
            edge_type=EdgeType.VOLUME,
            confidence=min((volume_ratio - self.min_volume_spike) / 5, 1.0),
            market_price=market_prob,
            your_estimate=None,
            expected_value=None,
            description=f"Volume spike: {volume_ratio:.1f}x avg ({current_volume:,})",
            metadata={
                "current_volume": current_volume,
                "avg_volume": avg_volume,
                "ratio": volume_ratio,
            },
        )

    def detect_volatility_edge(
        self,
        ticker: str,
        price_change: float,
        market_prob: float,
    ) -> Edge | None:
        """
        Detect unusual price movements.

        Large price changes might indicate:
        - New information
        - Overreaction / underreaction
        - Manipulation

        Args:
            ticker: Market ticker
            price_change: Absolute price change (0-1)
            market_prob: Current market probability

        Returns:
            Edge if detected, None otherwise
        """
        if abs(price_change) < self.min_price_move:
            return None

        direction = "up" if price_change > 0 else "down"

        return Edge(
            ticker=ticker,
            edge_type=EdgeType.VOLATILITY,
            confidence=min(abs(price_change) / 0.30, 1.0),  # Scale to 30%
            market_price=market_prob,
            your_estimate=None,
            expected_value=None,
            description=f"Large move {direction}: {price_change:+.1%}",
            metadata={"price_change": price_change, "direction": direction},
        )
