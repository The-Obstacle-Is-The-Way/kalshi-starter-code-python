"""Market scanner for finding opportunities."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Mapping

    from kalshi_research.api.models.market import Market

from kalshi_research.api.models.market import MarketStatus
from kalshi_research.constants import (
    DEFAULT_CLOSE_RACE_RANGE,
    DEFAULT_HIGH_VOLUME_THRESHOLD,
    DEFAULT_WIDE_SPREAD_THRESHOLD,
)


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

    def __init__(self, *, exchange_status: Mapping[str, object] | None = None) -> None:
        self._exchange_status = exchange_status

    def _is_exchange_tradeable(self) -> bool:
        if self._exchange_status is None:
            return True

        exchange_active = self._exchange_status.get("exchange_active")
        trading_active = self._exchange_status.get("trading_active")

        if not isinstance(exchange_active, bool) or not isinstance(trading_active, bool):
            return False

        return exchange_active and trading_active

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
        if not self._is_exchange_tradeable():
            return False

        now = datetime.now(UTC)

        # Check status
        if market.status != MarketStatus.ACTIVE:
            return False

        # Check timing - market must not be past close_time
        return now < market.close_time

    def verify_market_open(self, market: Market) -> None:
        """
        Verify market is open for trading, raise if not.

        Args:
            market: Market to verify

        Raises:
            MarketClosedError: If market is closed or not tradeable
        """
        if not self._is_exchange_tradeable():
            exchange_active = (
                self._exchange_status.get("exchange_active")
                if self._exchange_status is not None
                else None
            )
            trading_active = (
                self._exchange_status.get("trading_active")
                if self._exchange_status is not None
                else None
            )
            raise MarketClosedError(
                "Exchange trading is currently halted "
                f"(exchange_active={exchange_active}, trading_active={trading_active})"
            )

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
                # See scan_close_races:199-201 for binary market math derivation
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
                # See scan_close_races:199-201 for binary market math derivation
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
                # See scan_close_races:199-201 for binary market math derivation
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
