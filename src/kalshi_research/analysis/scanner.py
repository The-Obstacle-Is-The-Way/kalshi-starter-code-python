"""Market scanner for finding opportunities."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from kalshi_research.api.models.market import Market

# Re-export public API for backwards compatibility
from kalshi_research.analysis._scanner_models import (
    MarketClosedError,
    ScanFilter,
    ScanResult,
)
from kalshi_research.analysis._verifier import MarketStatusVerifier
from kalshi_research.constants import (
    DEFAULT_CLOSE_RACE_RANGE,
    DEFAULT_HIGH_VOLUME_THRESHOLD,
    DEFAULT_WIDE_SPREAD_THRESHOLD,
)

__all__ = [
    "MarketClosedError",
    "MarketScanner",
    "MarketStatusVerifier",
    "ScanFilter",
    "ScanResult",
]


class MarketScanner:
    """
    Scan markets for various opportunity types.

    Use cases:
    - Find markets near 50% (close races)
    - Find high-volume markets (active)
    - Find wide-spread markets (illiquid)
    - Find markets expiring soon
    """

    def __init__(
        self,
        close_race_range: tuple[float, float] = DEFAULT_CLOSE_RACE_RANGE,
        high_volume_threshold: int = DEFAULT_HIGH_VOLUME_THRESHOLD,
        wide_spread_threshold: int = DEFAULT_WIDE_SPREAD_THRESHOLD,
        verifier: MarketStatusVerifier | None = None,
    ) -> None:
        """
        Initialize the scanner.

        Args:
            close_race_range: Probability range for close races
            high_volume_threshold: 24h volume threshold
            wide_spread_threshold: Spread threshold in cents
            verifier: Optional MarketStatusVerifier (creates default if None)
        """
        self.close_race_range = close_race_range
        self.high_volume_threshold = high_volume_threshold
        self.wide_spread_threshold = wide_spread_threshold
        self.verifier = verifier or MarketStatusVerifier()

    def scan_close_races(
        self,
        markets: list[Market],
        top_n: int = 10,
        min_volume_24h: int = 0,
        max_spread: int = 100,
    ) -> list[ScanResult]:
        """
        Find markets near 50% probability.

        These are the most uncertain markets - ideal for
        research and finding edges.

        Args:
            markets: List of markets to scan
            top_n: Number of results to return
            min_volume_24h: Minimum 24h volume (default: 0)
            max_spread: Maximum bid-ask spread in cents (default: 100)

        Returns:
            List of ScanResults sorted by closeness to 50%
        """
        # Filter to only tradeable markets first
        tradeable_markets = self.verifier.filter_tradeable_markets(markets)
        results: list[ScanResult] = []

        for m in tradeable_markets:
            yes_bid = m.yes_bid_cents
            yes_ask = m.yes_ask_cents
            if yes_bid is None or yes_ask is None:
                continue
            # SKIP: Unpriced markets (0/0 or 0/100 placeholder quotes)
            if yes_bid == 0 and yes_ask == 0:
                continue  # No quotes at all
            if yes_bid == 0 and yes_ask == 100:
                continue  # Placeholder: no real price discovery

            spread = yes_ask - yes_bid

            # SKIP: Illiquid markets
            if spread > max_spread:
                continue
            if m.volume_24h < min_volume_24h:
                continue

            midpoint = (yes_bid + yes_ask) / 2
            prob = midpoint / 100.0

            # Check if in close race range
            if self.close_race_range[0] <= prob <= self.close_race_range[1]:
                # Score by closeness to 50%
                score = 1.0 - abs(prob - 0.5) * 2

                results.append(
                    ScanResult(
                        ticker=m.ticker,
                        title=m.title,
                        filter_type=ScanFilter.CLOSE_RACE,
                        score=score,
                        market_prob=prob,
                        volume_24h=m.volume_24h,
                        spread=spread,
                        details={"distance_from_50": abs(prob - 0.5)},
                    )
                )

        # Sort by score (closest to 50% first)
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_n]

    def scan_high_volume(
        self,
        markets: list[Market],
        top_n: int = 10,
    ) -> list[ScanResult]:
        """
        Find high-volume markets.

        High volume indicates:
        - Market interest
        - Liquidity
        - Active price discovery

        Args:
            markets: List of markets to scan
            top_n: Number of results to return

        Returns:
            List of ScanResults sorted by volume
        """
        # Filter to only tradeable markets first
        tradeable_markets = self.verifier.filter_tradeable_markets(markets)
        results: list[ScanResult] = []

        for m in tradeable_markets:
            if m.volume_24h >= self.high_volume_threshold:
                # Midpoint probability: convert cents to probability [0-1]
                spread = m.spread
                midpoint = m.midpoint
                if spread is None or midpoint is None:
                    continue
                prob = midpoint / 100.0

                # Score by volume (log scale)
                score = min(math.log10(m.volume_24h + 1) / 6, 1.0)

                results.append(
                    ScanResult(
                        ticker=m.ticker,
                        title=m.title,
                        filter_type=ScanFilter.HIGH_VOLUME,
                        score=score,
                        market_prob=prob,
                        volume_24h=m.volume_24h,
                        spread=spread,
                        details={"volume_rank_score": score},
                    )
                )

        results.sort(key=lambda r: r.volume_24h, reverse=True)
        return results[:top_n]

    def scan_wide_spread(
        self,
        markets: list[Market],
        top_n: int = 10,
    ) -> list[ScanResult]:
        """
        Find markets with wide bid-ask spreads.

        Wide spreads might indicate:
        - Market making opportunity
        - Low liquidity
        - Uncertainty

        Args:
            markets: List of markets to scan
            top_n: Number of results to return

        Returns:
            List of ScanResults sorted by spread
        """
        # Filter to only tradeable markets first
        tradeable_markets = self.verifier.filter_tradeable_markets(markets)
        results: list[ScanResult] = []

        for m in tradeable_markets:
            spread = m.spread
            if spread is None:
                continue

            if spread >= self.wide_spread_threshold:
                # Midpoint probability: convert cents to probability [0-1]
                midpoint = cast("float", m.midpoint)
                prob = midpoint / 100.0

                # Score by spread (capped at 20c)
                score = min(spread / 20, 1.0)

                results.append(
                    ScanResult(
                        ticker=m.ticker,
                        title=m.title,
                        filter_type=ScanFilter.WIDE_SPREAD,
                        score=score,
                        market_prob=prob,
                        volume_24h=m.volume_24h,
                        spread=spread,
                        details={"potential_capture": spread / 2},
                    )
                )

        results.sort(key=lambda r: r.spread, reverse=True)
        return results[:top_n]

    def scan_expiring_soon(
        self,
        markets: list[Market],
        hours: int = 24,
        top_n: int = 10,
    ) -> list[ScanResult]:
        """
        Find markets expiring within a time window.

        Markets near expiration often have:
        - Final price discovery
        - Resolution information
        - Last-minute volatility

        Args:
            markets: List of markets to scan
            hours: Hours until expiration
            top_n: Number of results to return

        Returns:
            List of ScanResults sorted by time to expiration
        """
        # Filter to only tradeable markets first
        tradeable_markets = self.verifier.filter_tradeable_markets(markets)
        results: list[ScanResult] = []
        cutoff = datetime.now(UTC) + timedelta(hours=hours)

        for m in tradeable_markets:
            if m.close_time <= cutoff:
                # Midpoint probability: convert cents to probability [0-1]
                spread = m.spread
                midpoint = m.midpoint
                if spread is None or midpoint is None:
                    continue
                prob = midpoint / 100.0

                time_left = m.close_time - datetime.now(UTC)
                hours_left = time_left.total_seconds() / 3600

                # Score by urgency (closer = higher score)
                score = max(0, 1.0 - hours_left / hours)

                results.append(
                    ScanResult(
                        ticker=m.ticker,
                        title=m.title,
                        filter_type=ScanFilter.EXPIRING_SOON,
                        score=score,
                        market_prob=prob,
                        volume_24h=m.volume_24h,
                        spread=spread,
                        details={
                            "hours_left": hours_left,
                            "close_time": m.close_time.isoformat(),
                        },
                    )
                )

        def get_hours_left(r: ScanResult) -> float:
            val = r.details.get("hours_left", 999.0)
            return float(val) if isinstance(val, int | float) else 999.0

        results.sort(key=get_hours_left)
        return results[:top_n]
