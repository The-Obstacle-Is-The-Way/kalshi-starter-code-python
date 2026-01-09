"""
Model tests - use REAL objects, NO MOCKS.

These tests verify that domain logic works correctly using actual
Pydantic model instances, not mocked stand-ins.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from kalshi_research.api.models.market import Market, MarketFilterStatus, MarketStatus
from kalshi_research.api.models.orderbook import Orderbook
from kalshi_research.api.models.trade import Trade


class TestMarketModel:
    """Test Market model with REAL instances."""

    def test_market_creation_from_api_data(self, make_market: Any) -> None:
        """Market model correctly parses API response data."""
        data = make_market(ticker="BTC-100K", yes_bid=45, yes_ask=47)

        market = Market.model_validate(data)

        assert market.ticker == "BTC-100K"
        assert market.yes_bid == 45
        assert market.yes_ask == 47
        assert market.status == MarketStatus.ACTIVE

    def test_market_status_enum_parsing(self) -> None:
        """Status string correctly maps to enum."""
        for status_str, expected_enum in [
            ("initialized", MarketStatus.INITIALIZED),
            ("active", MarketStatus.ACTIVE),
            ("inactive", MarketStatus.INACTIVE),
            ("closed", MarketStatus.CLOSED),
            ("determined", MarketStatus.DETERMINED),
            ("finalized", MarketStatus.FINALIZED),
        ]:
            market = Market.model_validate(
                {
                    "ticker": "TEST",
                    "event_ticker": "EVT",
                    "title": "Test",
                    "subtitle": "",
                    "status": status_str,
                    "result": "",
                    "yes_bid": 50,
                    "yes_ask": 50,
                    "no_bid": 50,
                    "no_ask": 50,
                    "volume": 0,
                    "volume_24h": 0,
                    "open_interest": 0,
                    "liquidity": 0,
                    "open_time": "2024-01-01T00:00:00Z",
                    "close_time": "2025-01-01T00:00:00Z",
                    "expiration_time": "2025-01-02T00:00:00Z",
                }
            )
            assert market.status == expected_enum

    def test_market_negative_liquidity_becomes_none(self, make_market: Any) -> None:
        """Negative liquidity values are converted to None (deprecated field)."""
        data = make_market(liquidity=-170750)
        market = Market.model_validate(data)
        # Validator converts negative to None (field deprecated Jan 15, 2026)
        assert market.liquidity is None

    def test_market_liquidity_optional(self, make_market: Any) -> None:
        """Liquidity field is optional (deprecated, may be absent)."""
        data = make_market()
        data.pop("liquidity", None)  # Remove liquidity field
        market = Market.model_validate(data)
        assert market.liquidity is None

    def test_market_positive_liquidity_preserved(self, make_market: Any) -> None:
        """Positive liquidity values are preserved until field removal."""
        data = make_market(liquidity=50000)
        market = Market.model_validate(data)
        assert market.liquidity == 50000

    def test_market_immutability(self, make_market: Any) -> None:
        """Market model is frozen (immutable)."""
        from pydantic import ValidationError

        market = Market.model_validate(make_market())

        with pytest.raises(ValidationError):
            market.ticker = "CHANGED"

    def test_market_filter_status_values(self) -> None:
        """Verify MarketFilterStatus values match API SSOT."""
        assert MarketFilterStatus.UNOPENED == "unopened"
        assert MarketFilterStatus.OPEN == "open"
        assert MarketFilterStatus.PAUSED == "paused"
        assert MarketFilterStatus.CLOSED == "closed"
        assert MarketFilterStatus.SETTLED == "settled"


class TestOrderbookModel:
    """Test Orderbook computed properties with REAL data."""

    def test_orderbook_best_bids(self) -> None:
        """Computed properties return correct best prices."""
        orderbook = Orderbook(
            yes=[(45, 100), (44, 200), (43, 500)],
            no=[(53, 150), (54, 250), (55, 400)],
        )

        assert orderbook.best_yes_bid == 45
        assert orderbook.best_no_bid == 55

    def test_orderbook_spread_calculation(self) -> None:
        """Spread = 100 - best_yes_bid - best_no_bid."""
        orderbook = Orderbook(
            yes=[(45, 100)],
            no=[(54, 100)],
        )

        # Spread = 100 - 45 - 54 = 1
        assert orderbook.spread == 1

    def test_orderbook_midpoint_calculation(self) -> None:
        """Midpoint uses implied ask from NO side."""
        orderbook = Orderbook(
            yes=[(45, 100)],
            no=[(54, 100)],
        )

        # Implied YES ask = 100 - best_no_bid = 100 - 54 = 46
        # Midpoint = (45 + 46) / 2 = 45.5
        assert orderbook.midpoint == Decimal("45.5")

    def test_orderbook_empty_sides(self) -> None:
        """Handle empty or None orderbook sides gracefully."""
        orderbook = Orderbook(yes=None, no=None)

        assert orderbook.best_yes_bid is None
        assert orderbook.best_no_bid is None
        assert orderbook.spread is None
        assert orderbook.midpoint is None

    @pytest.mark.parametrize(
        ("yes_bids", "no_bids", "expected_spread"),
        [
            ([(50, 100)], [(50, 100)], 0),  # Tight market
            ([(40, 100)], [(40, 100)], 20),  # Wide spread
            ([(1, 100)], [(1, 100)], 98),  # Extreme
        ],
    )
    def test_spread_various_scenarios(
        self,
        yes_bids: list[tuple[int, int]],
        no_bids: list[tuple[int, int]],
        expected_spread: int,
    ) -> None:
        """Spread calculation handles various market conditions."""
        orderbook = Orderbook(yes=yes_bids, no=no_bids)
        assert orderbook.spread == expected_spread


class TestTradeModel:
    """Test Trade model with REAL instances."""

    def test_trade_creation(self) -> None:
        """Trade model parses API data correctly."""
        trade = Trade(
            trade_id="abc123",
            ticker="BTC-100K",
            created_time=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
            yes_price=46,
            no_price=54,
            count=10,
            taker_side="yes",
        )

        assert trade.yes_price == 46
        assert trade.no_price == 54
        assert trade.count == 10

    def test_trade_prices_in_valid_range(self) -> None:
        """Prices must be in valid range (0-100)."""
        # Valid trade
        trade = Trade(
            trade_id="valid",
            ticker="TEST",
            created_time=datetime.now(UTC),
            yes_price=50,
            no_price=50,
            count=1,
            taker_side="yes",
        )
        assert trade.yes_price == 50

    def test_trade_count_must_be_positive(self) -> None:
        """Trade count must be at least 1."""
        with pytest.raises(ValueError):
            Trade(
                trade_id="bad",
                ticker="TEST",
                created_time=datetime.now(UTC),
                yes_price=50,
                no_price=50,
                count=0,  # Invalid - must be >= 1
                taker_side="yes",
            )
