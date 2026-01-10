from __future__ import annotations

from typing import Any

import pytest

from kalshi_research.analysis.liquidity import (
    LiquidityError,
    LiquidityGrade,
    OrderbookAnalyzer,
    enforce_max_slippage,
    estimate_slippage,
    liquidity_score,
    max_safe_order_size,
    orderbook_depth_score,
)
from kalshi_research.api.models.market import Market
from kalshi_research.api.models.orderbook import Orderbook


def test_orderbook_depth_empty_returns_zero() -> None:
    orderbook = Orderbook(yes=None, no=None)
    depth = orderbook_depth_score(orderbook)
    assert depth.total_contracts == 0
    assert depth.weighted_score == 0.0
    assert depth.yes_side_depth == 0
    assert depth.no_side_depth == 0


def test_orderbook_depth_single_level_scores_correctly() -> None:
    orderbook = Orderbook(yes=[(50, 100)], no=[(50, 100)])
    depth = orderbook_depth_score(orderbook, radius_cents=10)
    assert depth.total_contracts == 200
    assert depth.weighted_score > 0


def test_distance_weighting_prefers_near_mid() -> None:
    close = Orderbook(yes=[(50, 100)], no=[(50, 100)])
    far = Orderbook(yes=[(40, 100)], no=[(40, 100)])  # midpoint=50, all depth is 10c away
    assert orderbook_depth_score(close).weighted_score > orderbook_depth_score(far).weighted_score


def test_estimate_slippage_small_order_minimal_slippage() -> None:
    orderbook = Orderbook(yes=[(47, 1000)], no=[(53, 1000)])
    slip = estimate_slippage(orderbook, "yes", "buy", 10)
    assert slip.remaining_unfilled == 0
    assert slip.slippage_cents == 0
    assert slip.levels_crossed == 1


def test_estimate_slippage_large_order_walks_book() -> None:
    orderbook = Orderbook(yes=[(47, 1000)], no=[(53, 100), (52, 100), (51, 100)])
    slip = estimate_slippage(orderbook, "yes", "buy", 250)
    assert slip.remaining_unfilled == 0
    assert slip.levels_crossed == 3
    assert slip.slippage_cents > 0
    assert slip.avg_fill_price > slip.best_price


def test_estimate_slippage_unfillable_order_reports_remaining() -> None:
    orderbook = Orderbook(yes=[(47, 1000)], no=[(53, 50)])
    slip = estimate_slippage(orderbook, "yes", "buy", 1000)
    assert slip.fillable_quantity == 50
    assert slip.remaining_unfilled == 950


def test_enforce_max_slippage_raises_when_unfillable() -> None:
    orderbook = Orderbook(yes=[(47, 1000)], no=[(53, 50)])
    with pytest.raises(LiquidityError, match="Insufficient depth"):
        enforce_max_slippage(orderbook, "yes", "buy", quantity=1000, max_slippage_pct=5.0)


def test_enforce_max_slippage_raises_when_slippage_too_high() -> None:
    orderbook = Orderbook(yes=[(47, 1000)], no=[(53, 100), (52, 100), (51, 100)])
    with pytest.raises(LiquidityError, match="slippage"):
        enforce_max_slippage(orderbook, "yes", "buy", quantity=300, max_slippage_pct=0.5)


def test_enforce_max_slippage_returns_estimate_when_ok() -> None:
    orderbook = Orderbook(yes=[(47, 1000)], no=[(53, 100), (52, 100), (51, 100)])
    estimate = enforce_max_slippage(orderbook, "yes", "buy", quantity=100, max_slippage_pct=1.0)
    assert estimate.remaining_unfilled == 0


def test_max_safe_order_size_empty_orderbook_is_zero() -> None:
    orderbook = Orderbook(yes=None, no=None)
    assert max_safe_order_size(orderbook, "yes", max_slippage_cents=3) == 0


@pytest.mark.parametrize(
    ("max_slippage", "expected"),
    [
        (0, 100),  # only the best level is allowed
        (1, 300),  # can consume all three levels (avg fill 48c, slippage 1c)
    ],
)
def test_max_safe_order_size_respects_slippage(max_slippage: int, expected: int) -> None:
    orderbook = Orderbook(yes=[(47, 1000)], no=[(53, 100), (52, 100), (51, 100)])
    assert max_safe_order_size(orderbook, "yes", max_slippage_cents=max_slippage) == expected


def test_liquidity_score_in_range_and_grade(make_market: Any) -> None:
    market = Market.model_validate(make_market(volume_24h=7000, open_interest=3000))
    orderbook = Orderbook(yes=[(47, 500)], no=[(53, 500)])
    analysis = liquidity_score(market, orderbook)

    assert 0 <= analysis.score <= 100
    assert analysis.grade in LiquidityGrade
    assert analysis.max_safe_size_yes >= 0
    assert analysis.max_safe_size_no >= 0


def test_orderbook_analyzer_smoke(make_market: Any) -> None:
    analyzer = OrderbookAnalyzer()
    market = Market.model_validate(make_market(volume_24h=7000, open_interest=3000))
    orderbook = Orderbook(yes=[(47, 500)], no=[(53, 500)])
    analysis = analyzer.liquidity(market, orderbook)
    assert 0 <= analysis.score <= 100
