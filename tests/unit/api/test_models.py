"""
Model tests - use REAL objects, NO MOCKS.

These tests verify that domain logic works correctly using actual
Pydantic model instances, not mocked stand-ins.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
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

    def test_market_model_accepts_dollar_fields(self) -> None:
        """Market model should accept liquidity_dollars and notional_value_dollars."""
        market = Market.model_validate(
            {
                "ticker": "KXTEST",
                "event_ticker": "KXEVENT",
                "title": "Test Market",
                "status": "active",
                "result": "",
                "volume": 100,
                "volume_24h": 50,
                "open_interest": 10,
                "open_time": "2026-01-01T00:00:00Z",
                "close_time": "2026-01-15T00:00:00Z",
                "expiration_time": "2026-01-15T00:00:00Z",
                "liquidity_dollars": "1234.56",
                "notional_value_dollars": "5678.90",
            }
        )

        assert market.liquidity_dollars == "1234.56"
        assert market.notional_value_dollars == "5678.90"

    def test_market_model_dollar_fields_optional(self) -> None:
        """Dollar fields should be optional (None by default)."""
        market = Market.model_validate(
            {
                "ticker": "KXTEST",
                "event_ticker": "KXEVENT",
                "title": "Test Market",
                "status": "active",
                "result": "",
                "volume": 100,
                "volume_24h": 50,
                "open_interest": 10,
                "open_time": "2026-01-01T00:00:00Z",
                "close_time": "2026-01-15T00:00:00Z",
                "expiration_time": "2026-01-15T00:00:00Z",
            }
        )

        assert market.liquidity_dollars is None
        assert market.notional_value_dollars is None

    def test_market_positive_liquidity_preserved(self, make_market: Any) -> None:
        """Positive liquidity values are preserved until field removal."""
        data = make_market(liquidity=50000)
        market = Market.model_validate(data)
        assert market.liquidity == 50000

    def test_market_settlement_ts_parses(self, make_market: Any) -> None:
        """Market model parses settlement_ts when present."""
        data = make_market(
            status="finalized",
            result="yes",
            settlement_ts="2025-12-31T12:00:00Z",
            expiration_time="2026-01-01T00:00:00Z",
        )
        market = Market.model_validate(data)

        assert market.settlement_ts is not None
        assert market.settlement_ts < market.expiration_time

    def test_market_datetime_fields_are_normalized_to_utc(self) -> None:
        market = Market.model_validate(
            {
                "ticker": "TEST",
                "event_ticker": "EVT",
                "title": "Test",
                "subtitle": "",
                "status": "active",
                "result": "",
                "yes_bid": 50,
                "yes_ask": 50,
                "no_bid": 50,
                "no_ask": 50,
                "volume": 0,
                "volume_24h": 0,
                "open_interest": 0,
                "liquidity": 0,
                "created_time": "2024-01-01T00:00:00",
                "open_time": "2024-01-01T00:00:00",
                "close_time": "2025-01-01T00:00:00",
                "expiration_time": "2025-01-02T00:00:00",
                "settlement_ts": "2025-12-31T12:00:00",
            }
        )

        assert market.created_time is not None
        for dt in (
            market.created_time,
            market.open_time,
            market.close_time,
            market.expiration_time,
            market.settlement_ts,
        ):
            assert dt is not None
            assert dt.tzinfo is not None
            assert dt.utcoffset() == timedelta(0)

    def test_market_settlement_ts_optional(self, make_market: Any) -> None:
        """Market model accepts missing settlement_ts for unsettled/legacy markets."""
        market = Market.model_validate(make_market())
        assert market.settlement_ts is None

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

    # === Dollar field fallback tests (BUG-056 P0-1 fix) ===

    def test_orderbook_dollar_fallback_best_yes_bid(self) -> None:
        """best_yes_bid falls back to yes_dollars when yes is None."""
        # Simulates post-Jan 15, 2026 API response (no legacy cents field)
        orderbook = Orderbook(
            yes=None,
            no=None,
            yes_dollars=[("0.45", 100), ("0.44", 200), ("0.43", 500)],
            no_dollars=[("0.53", 150)],
        )

        # Should convert "0.45" to 45 cents
        assert orderbook.best_yes_bid == 45

    def test_orderbook_dollar_fallback_best_no_bid(self) -> None:
        """best_no_bid falls back to no_dollars when no is None."""
        orderbook = Orderbook(
            yes=None,
            no=None,
            yes_dollars=[("0.45", 100)],
            no_dollars=[("0.53", 150), ("0.54", 250), ("0.55", 400)],
        )

        # Should convert "0.55" (max) to 55 cents
        assert orderbook.best_no_bid == 55

    def test_orderbook_dollar_fallback_spread(self) -> None:
        """Spread works with dollar-only orderbook."""
        orderbook = Orderbook(
            yes_dollars=[("0.45", 100)],
            no_dollars=[("0.54", 100)],
        )

        # Spread = 100 - 45 - 54 = 1
        assert orderbook.spread == 1

    def test_orderbook_dollar_fallback_midpoint(self) -> None:
        """Midpoint works with dollar-only orderbook."""
        orderbook = Orderbook(
            yes_dollars=[("0.45", 100)],
            no_dollars=[("0.54", 100)],
        )

        # Implied YES ask = 100 - 54 = 46
        # Midpoint = (45 + 46) / 2 = 45.5
        assert orderbook.midpoint == Decimal("45.5")

    def test_orderbook_dollars_preferred_over_legacy_cents(self) -> None:
        """When both dollar and legacy fields present, prefer dollars (forward-compatible)."""
        orderbook = Orderbook(
            yes=[(45, 100)],  # Legacy cents
            no=[(54, 100)],  # Legacy cents
            yes_dollars=[("0.99", 100)],  # Different dollar value
            no_dollars=[("0.01", 100)],  # Different dollar value
        )

        # Should use dollars, not legacy cents
        assert orderbook.best_yes_bid == 99
        assert orderbook.best_no_bid == 1

    def test_orderbook_dollar_precision(self) -> None:
        """Dollar string conversion handles various precision values."""
        orderbook = Orderbook(
            yes_dollars=[("0.50", 100), ("0.5", 50)],  # Both "0.50" and "0.5" valid
            no_dollars=[("0.01", 100)],  # Minimum
        )

        assert orderbook.best_yes_bid == 50
        assert orderbook.best_no_bid == 1

    # === Level accessor tests (forward-compatible API) ===

    def test_orderbook_yes_levels_from_legacy(self) -> None:
        """yes_levels returns legacy cents when available."""
        orderbook = Orderbook(
            yes=[(45, 100), (44, 200)],
            no=[(54, 100)],
        )

        assert orderbook.yes_levels == [(45, 100), (44, 200)]

    def test_orderbook_no_levels_from_legacy(self) -> None:
        """no_levels returns legacy cents when available."""
        orderbook = Orderbook(
            yes=[(45, 100)],
            no=[(54, 100), (55, 200)],
        )

        assert orderbook.no_levels == [(54, 100), (55, 200)]

    def test_orderbook_yes_levels_from_dollars(self) -> None:
        """yes_levels falls back to dollar conversion when legacy is None."""
        orderbook = Orderbook(
            yes=None,
            yes_dollars=[("0.45", 100), ("0.44", 200)],
        )

        # Should convert dollar strings to cents
        assert orderbook.yes_levels == [(45, 100), (44, 200)]

    def test_orderbook_no_levels_from_dollars(self) -> None:
        """no_levels falls back to dollar conversion when legacy is None."""
        orderbook = Orderbook(
            no=None,
            no_dollars=[("0.54", 100), ("0.55", 200)],
        )

        assert orderbook.no_levels == [(54, 100), (55, 200)]

    def test_orderbook_levels_empty_when_none(self) -> None:
        """Level accessors return empty list when both fields are None."""
        orderbook = Orderbook()

        assert orderbook.yes_levels == []
        assert orderbook.no_levels == []

    def test_orderbook_levels_prefer_legacy_over_dollars(self) -> None:
        """Level accessors prefer dollars when both present (forward-compatible)."""
        orderbook = Orderbook(
            yes=[(45, 100)],
            no=[(54, 100)],
            yes_dollars=[("0.99", 100)],  # Different value
            no_dollars=[("0.01", 100)],  # Different value
        )

        # Should use dollars, not legacy
        assert orderbook.yes_levels == [(99, 100)]
        assert orderbook.no_levels == [(1, 100)]


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
