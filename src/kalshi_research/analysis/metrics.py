"""Market efficiency metrics and analysis tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Sequence

    from kalshi_research.api.models import Market
    from kalshi_research.data.models import PriceSnapshot


@dataclass
class SpreadStats:
    """Spread statistics for a market."""

    ticker: str
    current_spread: int  # Current bid-ask spread (cents)
    avg_spread: float  # Average spread over period
    min_spread: int  # Minimum spread seen
    max_spread: int  # Maximum spread seen
    relative_spread: float  # Spread / midpoint
    n_samples: int


@dataclass
class VolatilityStats:
    """Volatility statistics for a market."""

    ticker: str
    daily_volatility: float  # Annualized daily vol
    hourly_volatility: float  # Hourly vol
    max_daily_move: float  # Largest single-day move
    avg_abs_return: float  # Average absolute return
    period_days: int


@dataclass
class VolumeProfile:
    """Volume distribution over time."""

    ticker: str
    hourly_volume: dict[int, float]  # Hour (0-23) -> avg volume
    daily_volume: dict[str, float]  # Weekday -> avg volume
    total_volume: int
    period_days: int


class MarketMetrics:
    """
    Compute market efficiency and trading metrics.

    Usage:
        metrics = MarketMetrics()
        spread = metrics.compute_spread_stats(market, snapshots)
        vol = metrics.compute_volatility(snapshots)
    """

    def compute_spread_stats(
        self,
        market: Market,
        snapshots: Sequence[PriceSnapshot] | None = None,
    ) -> SpreadStats:
        """
        Compute spread statistics.

        Args:
            market: Current market data
            snapshots: Historical snapshots (optional, for averages)

        Returns:
            SpreadStats with current and historical spread info
        """
        current_spread = market.spread
        midpoint = market.midpoint

        if snapshots and len(snapshots) > 0:
            spreads = [s.spread for s in snapshots]
            avg_spread = float(np.mean(spreads))
            min_spread = min(spreads)
            max_spread = max(spreads)
            n_samples = len(snapshots)
        else:
            avg_spread = float(current_spread)
            min_spread = current_spread
            max_spread = current_spread
            n_samples = 1

        relative_spread = current_spread / midpoint if midpoint > 0 else 0.0

        return SpreadStats(
            ticker=market.ticker,
            current_spread=current_spread,
            avg_spread=avg_spread,
            min_spread=min_spread,
            max_spread=max_spread,
            relative_spread=relative_spread,
            n_samples=n_samples,
        )

    def compute_volatility(
        self,
        snapshots: Sequence[PriceSnapshot],
        annualize: bool = True,
    ) -> VolatilityStats | None:
        """
        Compute volatility statistics from price snapshots.

        Args:
            snapshots: Historical price snapshots
            annualize: Whether to annualize volatility

        Returns:
            VolatilityStats or None if insufficient data
        """
        if len(snapshots) < 2:
            return None

        ticker = snapshots[0].ticker

        # Sort by timestamp
        sorted_snaps = sorted(snapshots, key=lambda s: s.snapshot_time)

        # Compute returns using midpoint as "yes_price"
        prices = np.array([s.midpoint / 100.0 for s in sorted_snaps], dtype=float)
        prev_prices = prices[:-1]
        diffs = np.diff(prices)

        # Avoid divide-by-zero warnings (and filter out invalid returns below).
        with np.errstate(divide="ignore", invalid="ignore"):
            returns = np.divide(
                diffs,
                prev_prices,
                out=np.full_like(diffs, np.nan, dtype=float),
                where=prev_prices != 0,
            )

        # Handle edge cases (0 prices, inf/nan)
        returns = returns[np.isfinite(returns)]

        if len(returns) < 2:
            return None

        # Compute stats
        hourly_vol = float(np.std(returns))

        # Time span for annualization
        time_span = sorted_snaps[-1].snapshot_time - sorted_snaps[0].snapshot_time
        period_days = max(1, time_span.days)

        # Annualize (assuming ~24 hours/day for hourly sampling)
        daily_vol = hourly_vol * np.sqrt(24) if annualize else hourly_vol

        # Daily returns for max move
        daily_returns = self._compute_daily_returns(sorted_snaps)
        max_daily = max(abs(r) for r in daily_returns) if daily_returns else 0.0

        return VolatilityStats(
            ticker=ticker,
            daily_volatility=daily_vol,
            hourly_volatility=hourly_vol,
            max_daily_move=max_daily,
            avg_abs_return=float(np.mean(np.abs(returns))),
            period_days=period_days,
        )

    def compute_volume_profile(
        self,
        snapshots: Sequence[PriceSnapshot],
    ) -> VolumeProfile | None:
        """
        Compute volume distribution by time of day and day of week.

        Args:
            snapshots: Historical snapshots with volume data

        Returns:
            VolumeProfile or None if no data
        """
        if not snapshots:
            return None

        ticker = snapshots[0].ticker

        # Group by hour
        hourly: dict[int, list[int]] = {h: [] for h in range(24)}
        daily: dict[str, list[int]] = {
            "Mon": [],
            "Tue": [],
            "Wed": [],
            "Thu": [],
            "Fri": [],
            "Sat": [],
            "Sun": [],
        }
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        for snap in snapshots:
            hour = snap.snapshot_time.hour
            weekday = day_names[snap.snapshot_time.weekday()]
            vol = snap.volume

            hourly[hour].append(vol)
            daily[weekday].append(vol)

        # Compute averages
        hourly_avg = {h: float(np.mean(v)) if v else 0.0 for h, v in hourly.items()}
        daily_avg = {d: float(np.mean(v)) if v else 0.0 for d, v in daily.items()}

        time_span = max(s.snapshot_time for s in snapshots) - min(
            s.snapshot_time for s in snapshots
        )

        return VolumeProfile(
            ticker=ticker,
            hourly_volume=hourly_avg,
            daily_volume=daily_avg,
            total_volume=sum(s.volume for s in snapshots),
            period_days=max(1, time_span.days),
        )

    def _compute_daily_returns(
        self,
        snapshots: Sequence[PriceSnapshot],
    ) -> list[float]:
        """Compute daily returns from snapshots."""
        # Group by date
        by_date: dict[str, list[float]] = {}
        for snap in snapshots:
            date_key = snap.snapshot_time.date().isoformat()
            if date_key not in by_date:
                by_date[date_key] = []
            # Use midpoint as price
            price = snap.midpoint / 100.0
            by_date[date_key].append(price)

        # Compute daily close-to-close returns
        dates = sorted(by_date.keys())
        returns: list[float] = []

        for i in range(1, len(dates)):
            prev_close = by_date[dates[i - 1]][-1]
            curr_close = by_date[dates[i]][-1]
            if prev_close > 0:
                returns.append((curr_close - prev_close) / prev_close)

        return returns
