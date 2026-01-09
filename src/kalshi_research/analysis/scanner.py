"""Market scanner for finding opportunities."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kalshi_research.api.models.market import Market

from kalshi_research.api.models.market import MarketStatus


class MarketClosedError(Exception):
    """Raised when attempting to operate on a closed market."""

    pass


class MarketStatusVerifier:
    """
    Centralized market timing and status verification.

    Checks if markets are:
    - Still open for trading (not closed)
    - Active (not settled, finalized, etc.)
    - Valid for current operations
    """

    def is_market_tradeable(self, market: Market) -> bool:
        """
        Check if a market is currently tradeable.

        A market is tradeable if:
        1. Status is 'active'
        2. Current time < close_time

        Args:
            market: Market to check

        Returns:
            True if market is tradeable, False otherwise
        """
        now = datetime.now(UTC)

        # Check status
        if market.status != MarketStatus.ACTIVE:
            return False

        # Check timing - market must not be past close_time
        return not now >= market.close_time

    def verify_market_open(self, market: Market) -> None:
        """
        Verify market is open for trading, raise if not.

        Args:
            market: Market to verify

        Raises:
            MarketClosedError: If market is closed or not tradeable
        """
        if not self.is_market_tradeable(market):
            now = datetime.now(UTC)
            if market.status != MarketStatus.ACTIVE:
                raise MarketClosedError(
                    f"Market {market.ticker} has status {market.status.value}, "
                    f"expected {MarketStatus.ACTIVE.value}"
                )
            if now >= market.close_time:
                raise MarketClosedError(
                    f"Market {market.ticker} closed at {market.close_time.isoformat()}, "
                    f"current time is {now.isoformat()}"
                )

    def filter_tradeable_markets(self, markets: list[Market]) -> list[Market]:
        """
        Filter a list of markets to only tradeable ones.

        Args:
            markets: List of markets to filter

        Returns:
            List of tradeable markets
        """
        return [m for m in markets if self.is_market_tradeable(m)]


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
        close_race_range: tuple[float, float] = (0.40, 0.60),
        high_volume_threshold: int = 10000,
        wide_spread_threshold: int = 5,
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
            # SKIP: Unpriced markets (0/0 or 0/100 placeholder quotes)
            if m.yes_bid_cents == 0 and m.yes_ask_cents == 0:
                continue  # No quotes at all
            if m.yes_bid_cents == 0 and m.yes_ask_cents == 100:
                continue  # Placeholder: no real price discovery

            spread = m.spread

            # SKIP: Illiquid markets
            if spread > max_spread:
                continue
            if m.volume_24h < min_volume_24h:
                continue

            # Calculate probability from midpoint.
            # 200.0 = (bid + ask) / 2 for midpoint, then / 100 to convert cents to probability.
            # This is NOT a magic number - it's standard binary market math.
            # See: docs/_vendor-docs/kalshi-api-reference.md (Binary market math)
            prob = m.midpoint / 100.0

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
                # Midpoint probability: see scan_close_races for derivation of 200.0
                prob = m.midpoint / 100.0
                spread = m.spread

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

            if spread >= self.wide_spread_threshold:
                prob = m.midpoint / 100.0

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
                prob = m.midpoint / 100.0
                spread = m.spread

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

    def scan_all(
        self,
        markets: list[Market],
        top_n: int = 5,
    ) -> dict[ScanFilter, list[ScanResult]]:
        """
        Run all scans and return results grouped by filter.

        Args:
            markets: List of markets to scan
            top_n: Number of results per filter

        Returns:
            Dictionary mapping filter type to results
        """
        return {
            ScanFilter.CLOSE_RACE: self.scan_close_races(markets, top_n),
            ScanFilter.HIGH_VOLUME: self.scan_high_volume(markets, top_n),
            ScanFilter.WIDE_SPREAD: self.scan_wide_spread(markets, top_n),
            ScanFilter.EXPIRING_SOON: self.scan_expiring_soon(markets, top_n=top_n),
        }
