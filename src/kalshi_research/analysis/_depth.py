"""Orderbook depth analysis for liquidity scoring.

Provides distance-weighted depth scoring around the orderbook midpoint.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from kalshi_research.analysis._liquidity_models import DepthAnalysis
from kalshi_research.constants import DEFAULT_DEPTH_RADIUS_CENTS

if TYPE_CHECKING:
    from decimal import Decimal

    from kalshi_research.api.models.orderbook import Orderbook


def orderbook_depth_score(
    orderbook: Orderbook, *, radius_cents: int = DEFAULT_DEPTH_RADIUS_CENTS
) -> DepthAnalysis:
    """Calculate a distance-weighted depth score around the YES midpoint.

    Notes:
        - YES bids are already in YES-price terms.
        - NO bids imply YES asks at (100 - no_bid_price). We convert NO bids to implied YES asks
          for distance calculations so both sides are comparable around the same midpoint.
    """
    if radius_cents < 0:
        raise ValueError("radius_cents must be >= 0")

    midpoint: Decimal | None = orderbook.midpoint
    if midpoint is None:
        return DepthAnalysis(0, 0.0, 0, 0, 0.0)

    midpoint_float = float(midpoint)
    weighted_score = 0.0
    yes_depth = 0
    no_depth = 0

    # YES side: bids in YES cents
    for price, qty in orderbook.yes_levels:
        distance = abs(price - midpoint_float)
        if distance <= radius_cents:
            weight = 1.0 if radius_cents == 0 else 1.0 - (distance / (radius_cents + 1))
            weighted_score += qty * weight
            yes_depth += qty

    # NO side: bids in NO cents, convert to implied YES asks for distance-from-midpoint comparisons
    for no_price, qty in orderbook.no_levels:
        implied_yes_ask = 100 - no_price
        distance = abs(implied_yes_ask - midpoint_float)
        if distance <= radius_cents:
            weight = 1.0 if radius_cents == 0 else 1.0 - (distance / (radius_cents + 1))
            weighted_score += qty * weight
            no_depth += qty

    total = yes_depth + no_depth
    imbalance = (yes_depth - no_depth) / max(total, 1)

    return DepthAnalysis(
        total_contracts=total,
        weighted_score=weighted_score,
        yes_side_depth=yes_depth,
        no_side_depth=no_depth,
        imbalance_ratio=imbalance,
    )
