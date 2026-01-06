"""
Unit tests for clients module.

Tests the existing Kalshi client infrastructure.
Uses mocking ONLY at HTTP boundaries.
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from kalshi_research.clients import Environment


class TestEnvironment:
    """Tests for Environment enum."""

    def test_environment_demo_value(self) -> None:
        """Test DEMO environment has correct value."""
        assert Environment.DEMO.value == "demo"

    def test_environment_prod_value(self) -> None:
        """Test PROD environment has correct value."""
        assert Environment.PROD.value == "prod"

    def test_environment_values_are_unique(self) -> None:
        """Test all environment values are unique."""
        values = [e.value for e in Environment]
        assert len(values) == len(set(values))


class TestMarketDataFactories:
    """Tests for test fixture factories - validate they create consistent data."""

    def test_make_market_default_values(self, make_market: Any) -> None:
        """Test make_market creates valid default market data."""
        market = cast("dict[str, Any]", make_market())

        assert market["ticker"] == "TEST-MARKET"
        assert market["status"] == "active"
        assert market["yes_bid"] == 45
        assert market["yes_ask"] == 47

    def test_make_market_price_consistency(self, make_market: Any) -> None:
        """Test yes/no prices are consistent (sum to 100)."""
        market = cast("dict[str, Any]", make_market(yes_bid=40, yes_ask=45))

        # no_bid = 100 - yes_ask, no_ask = 100 - yes_bid
        assert market["no_bid"] == 55  # 100 - 45
        assert market["no_ask"] == 60  # 100 - 40
        # Verify the math holds
        assert market["yes_bid"] + market["no_ask"] == 100
        assert market["yes_ask"] + market["no_bid"] == 100

    def test_make_market_custom_overrides(self, make_market: Any) -> None:
        """Test make_market accepts custom overrides."""
        market = cast("dict[str, Any]", make_market(ticker="CUSTOM-123", volume=50000))

        assert market["ticker"] == "CUSTOM-123"
        assert market["volume"] == 50000

    def test_make_orderbook_default_values(self, make_orderbook: Any) -> None:
        """Test make_orderbook creates valid default orderbook data."""
        orderbook = cast("dict[str, list[list[int]]]", make_orderbook())

        assert len(orderbook["yes"]) == 3
        assert len(orderbook["no"]) == 3
        # First element of yes should be best bid (price, qty)
        assert orderbook["yes"][0] == [45, 100]

    def test_make_orderbook_custom_bids(self, make_orderbook: Any) -> None:
        """Test make_orderbook accepts custom bids."""
        orderbook = cast(
            "dict[str, list[list[int]]]",
            make_orderbook(yes_bids=[(50, 200), (49, 300)]),
        )

        assert orderbook["yes"] == [[50, 200], [49, 300]]

    def test_make_trade_default_values(self, make_trade: Any) -> None:
        """Test make_trade creates valid default trade data."""
        trade = cast("dict[str, Any]", make_trade())

        assert trade["ticker"] == "TEST-MARKET"
        assert trade["yes_price"] == 46
        assert trade["no_price"] == 54  # 100 - 46
        assert trade["count"] == 10

    def test_make_trade_price_consistency(self, make_trade: Any) -> None:
        """Test yes_price + no_price = 100."""
        trade = cast("dict[str, Any]", make_trade(yes_price=75))

        assert trade["yes_price"] + trade["no_price"] == 100


class TestFixedClock:
    """Tests for the fixed clock fixture."""

    def test_fixed_clock_returns_same_time(self, fixed_clock: Any) -> None:
        """Test fixed_clock always returns the same time."""
        time1 = fixed_clock()
        time2 = fixed_clock()

        assert time1 == time2

    def test_fixed_clock_has_time_attribute(self, fixed_clock: Any) -> None:
        """Test fixed_clock.time gives direct access to the fixed time."""
        assert fixed_clock() == fixed_clock.time

    def test_fixed_clock_is_timezone_aware(self, fixed_clock: Any) -> None:
        """Test the fixed time is timezone-aware."""
        assert fixed_clock.time.tzinfo is not None


class TestSpreadCalculation:
    """Tests for spread calculation logic - pure math, no mocks needed."""

    @pytest.mark.parametrize(
        ("yes_bid", "yes_ask", "expected_spread"),
        [
            (45, 47, 2),
            (50, 50, 0),
            (10, 90, 80),
            (1, 99, 98),
        ],
    )
    def test_spread_calculation(self, yes_bid: int, yes_ask: int, expected_spread: int) -> None:
        """Test spread = yes_ask - yes_bid."""
        spread = yes_ask - yes_bid
        assert spread == expected_spread

    @pytest.mark.parametrize(
        ("yes_bid", "yes_ask", "expected_midpoint"),
        [
            (45, 47, 46),
            (50, 50, 50),
            (10, 90, 50),
        ],
    )
    def test_midpoint_calculation(self, yes_bid: int, yes_ask: int, expected_midpoint: int) -> None:
        """Test midpoint = (yes_bid + yes_ask) / 2."""
        midpoint = (yes_bid + yes_ask) // 2
        assert midpoint == expected_midpoint


class TestPriceConversions:
    """Tests for price to probability conversions - pure math."""

    @pytest.mark.parametrize(
        ("price", "expected_probability"),
        [
            (50, 0.50),
            (75, 0.75),
            (1, 0.01),
            (99, 0.99),
        ],
    )
    def test_price_to_probability(self, price: int, expected_probability: float) -> None:
        """Test conversion from Kalshi price (cents) to probability."""
        probability = price / 100
        assert probability == expected_probability

    @pytest.mark.parametrize("price", [1, 25, 50, 75, 99])
    def test_probability_is_in_valid_range(self, price: int) -> None:
        """Test all valid prices convert to probabilities in (0, 1)."""
        probability = price / 100
        assert 0 < probability < 1
