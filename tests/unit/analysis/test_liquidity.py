from __future__ import annotations

from typing import Any

import pytest

from kalshi_research.analysis.liquidity import (
    LiquidityError,
    LiquidityGrade,
    LiquidityWeights,
    OrderbookAnalyzer,
    enforce_max_slippage,
    estimate_price_impact,
    estimate_slippage,
    liquidity_score,
    max_safe_order_size,
    orderbook_depth_score,
    suggest_execution_timing,
)
from kalshi_research.api.models.market import Market
from kalshi_research.api.models.orderbook import Orderbook


def test_orderbook_depth_rejects_negative_radius() -> None:
    orderbook = Orderbook(yes=[(50, 1)], no=[(50, 1)])
    with pytest.raises(ValueError, match="radius_cents"):
        orderbook_depth_score(orderbook, radius_cents=-1)


def test_orderbook_depth_radius_zero_counts_only_exact_mid() -> None:
    # midpoint=50 (best_yes_bid=50, best_no_bid=50 -> implied_yes_ask=50)
    orderbook = Orderbook(yes=[(50, 10), (40, 10)], no=[(50, 10), (40, 10)])
    depth = orderbook_depth_score(orderbook, radius_cents=0)

    # Only the exact-mid levels are counted when radius=0.
    assert depth.total_contracts == 20
    assert depth.weighted_score == 20.0


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


def test_estimate_slippage_rejects_non_positive_quantity() -> None:
    orderbook = Orderbook(yes=[(47, 1000)], no=[(53, 1000)])
    with pytest.raises(ValueError, match="quantity"):
        estimate_slippage(orderbook, "yes", "buy", 0)


def test_estimate_slippage_missing_side_returns_unfillable() -> None:
    # Buying YES requires NO bids (implied YES asks). With no NO side, it is unfillable.
    orderbook = Orderbook(yes=[(47, 1000)], no=None)
    slip = estimate_slippage(orderbook, "yes", "buy", 10)
    assert slip.fillable_quantity == 0
    assert slip.remaining_unfilled == 10


def test_estimate_slippage_sell_yes_skips_zero_quantity_levels() -> None:
    orderbook = Orderbook(yes=[(43, 0), (42, 10)], no=None)
    slip = estimate_slippage(orderbook, "yes", "sell", 10)
    assert slip.best_price == 43
    assert slip.avg_fill_price == 42.0
    assert slip.slippage_cents == 1.0
    assert slip.levels_crossed == 1


def test_estimate_slippage_buy_no_uses_implied_no_asks() -> None:
    orderbook = Orderbook(yes=[(60, 10), (55, 10)], no=None)
    slip = estimate_slippage(orderbook, "no", "buy", 15)
    assert slip.best_price == 40  # implied NO ask from YES 60 bid
    assert slip.levels_crossed == 2
    assert slip.slippage_cents > 0


def test_estimate_slippage_sell_no_uses_no_bids() -> None:
    orderbook = Orderbook(yes=None, no=[(45, 10), (40, 10)])
    slip = estimate_slippage(orderbook, "no", "sell", 15)
    assert slip.best_price == 45
    assert slip.levels_crossed == 2
    assert slip.slippage_cents > 0


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


def test_enforce_max_slippage_rejects_negative_max_pct() -> None:
    orderbook = Orderbook(yes=[(47, 1000)], no=[(53, 1000)])
    with pytest.raises(ValueError, match="max_slippage_pct"):
        enforce_max_slippage(orderbook, "yes", "buy", quantity=10, max_slippage_pct=-0.1)


def test_max_safe_order_size_empty_orderbook_is_zero() -> None:
    orderbook = Orderbook(yes=None, no=None)
    assert max_safe_order_size(orderbook, "yes", max_slippage_cents=3) == 0


def test_max_safe_order_size_rejects_negative_max_slippage_cents() -> None:
    orderbook = Orderbook(yes=[(47, 1000)], no=[(53, 1000)])
    with pytest.raises(ValueError, match="max_slippage_cents"):
        max_safe_order_size(orderbook, "yes", max_slippage_cents=-1)


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


@pytest.mark.parametrize(
    ("spread", "expected_grade"),
    [
        (1, LiquidityGrade.LIQUID),
        (10, LiquidityGrade.MODERATE),
        (15, LiquidityGrade.THIN),
        (20, LiquidityGrade.ILLIQUID),
    ],
)
def test_liquidity_score_grades_and_warnings(
    make_market: Any, spread: int, expected_grade: LiquidityGrade
) -> None:
    # Construct an orderbook with a controlled spread: spread = 100 - best_yes - best_no.
    best_yes = 40
    best_no = 60 - spread
    orderbook = Orderbook(yes=[(best_yes, 60)], no=[(best_no, 10)])
    market = Market.model_validate(make_market(volume_24h=100, open_interest=0))

    # Use spread-only weights so grade thresholds are driven by spread_score.
    weights = LiquidityWeights(spread=1.0, depth=0.0, volume=0.0, open_interest=0.0)
    analysis = liquidity_score(market, orderbook, weights=weights)

    assert analysis.grade == expected_grade
    assert any("Low volume" in warning for warning in analysis.warnings)
    if spread > 10:
        assert any("Wide spread" in warning for warning in analysis.warnings)


@pytest.mark.parametrize(
    ("yes_qty", "no_qty", "expected_side"),
    [
        (200, 10, "YES"),
        (10, 200, "NO"),
    ],
)
def test_liquidity_score_warns_on_imbalance(
    make_market: Any, yes_qty: int, no_qty: int, expected_side: str
) -> None:
    orderbook = Orderbook(yes=[(47, yes_qty)], no=[(53, no_qty)])
    market = Market.model_validate(make_market(volume_24h=10_000, open_interest=10_000))

    analysis = liquidity_score(market, orderbook)
    assert any(expected_side in warning for warning in analysis.warnings if "imbalance" in warning)


def test_estimate_price_impact_validation_and_cap(make_market: Any) -> None:
    market = Market.model_validate(make_market(volume_24h=0, open_interest=0))
    orderbook = Orderbook(yes=[(47, 100)], no=None)  # spread=None -> fallback to 10

    with pytest.raises(ValueError, match="order_quantity"):
        estimate_price_impact(market, orderbook, order_quantity=0)

    with pytest.raises(ValueError, match="impact_factor"):
        estimate_price_impact(market, orderbook, order_quantity=10, impact_factor=-0.1)

    impact = estimate_price_impact(market, orderbook, order_quantity=10_000, impact_factor=1.0)
    assert impact == 50.0


def test_liquidity_weights_reject_invalid_sum() -> None:
    with pytest.raises(ValueError, match=r"sum to 1\.0"):
        LiquidityWeights(spread=0.5, depth=0.5, volume=0.5, open_interest=0.0)


def test_suggest_execution_timing_has_expected_windows() -> None:
    window = suggest_execution_timing()
    assert 13 in window.optimal_hours_utc
    assert 0 in window.avoid_hours_utc
    assert "US" in window.reasoning


def test_orderbook_analyzer_smoke(make_market: Any) -> None:
    analyzer = OrderbookAnalyzer()
    market = Market.model_validate(make_market(volume_24h=7000, open_interest=3000))
    orderbook = Orderbook(yes=[(47, 500)], no=[(53, 500)])
    analysis = analyzer.liquidity(market, orderbook)
    assert 0 <= analysis.score <= 100


def test_orderbook_analyzer_delegates_methods(make_market: Any) -> None:
    analyzer = OrderbookAnalyzer(radius_cents=0)
    market = Market.model_validate(make_market(volume_24h=7000, open_interest=3000))
    orderbook = Orderbook(yes=[(50, 10), (40, 10)], no=[(50, 10), (40, 10)])

    assert analyzer.depth(orderbook) == orderbook_depth_score(orderbook, radius_cents=0)
    assert analyzer.slippage(orderbook, "yes", "buy", quantity=5) == estimate_slippage(
        orderbook, "yes", "buy", 5
    )
    assert analyzer.max_safe_buy_size(
        orderbook, "yes", max_slippage_cents=0
    ) == max_safe_order_size(orderbook, "yes", max_slippage_cents=0)
    assert analyzer.liquidity(market, orderbook) == liquidity_score(market, orderbook)
