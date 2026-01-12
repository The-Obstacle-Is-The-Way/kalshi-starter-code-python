"""
Shared test fixtures.

PHILOSOPHY: Use REAL objects wherever possible. Only mock at system boundaries.
- Real Pydantic models (not dicts pretending to be models)
- Real SQLite in-memory for repository tests
- respx ONLY for HTTP boundary
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from dotenv import load_dotenv

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

# Load environment variables from .env for integration tests
load_dotenv()


# ============================================================================
# API Credentials (for integration tests only)
# ============================================================================
@pytest.fixture(scope="session")
def api_credentials() -> dict[str, str | None]:
    """API credentials from environment (may be None for public-only tests)."""
    return {
        "key_id": os.getenv("KALSHI_KEY_ID"),
        "private_key_path": os.getenv("KALSHI_PRIVATE_KEY_PATH"),
        "environment": os.getenv("KALSHI_ENVIRONMENT", "demo"),
    }


# ============================================================================
# Database Fixtures (REAL in-memory SQLite, not mocks)
# ============================================================================
@pytest.fixture
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create real async SQLite engine for testing."""
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create real database session with schema.

    Note: After Phase 3, import Base from kalshi_research.data.models
    and create all tables before yielding the session.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        yield session


# ============================================================================
# Domain Object Builders (create REAL objects, not dicts)
# ============================================================================
# NOTE: These return dicts that match API response structure.
# After Phase 2, update to return REAL Pydantic models.


@pytest.fixture
def make_market() -> Callable[..., dict[str, Any]]:
    """Factory to create REAL Market objects with sensible defaults.

    Note: After Phase 2, update to return REAL Market Pydantic models.
    """

    fixture_path = (
        Path(__file__).resolve().parent / "fixtures" / "golden" / "market_single_response.json"
    )
    fixture_data = json.loads(fixture_path.read_text())
    fixture_market = fixture_data.get("response", {}).get("market")
    if not isinstance(fixture_market, dict):
        raise TypeError(
            "Golden market fixture has unexpected shape (expected response.market object)."
        )

    market_template: dict[str, Any] = dict(fixture_market)
    market_template["liquidity"] = None  # deprecated field; avoid accidental reliance in tests

    def _cents_to_fixed_dollars(cents: int) -> str:
        return f"{cents / 100:.4f}"

    def _make(
        ticker: str = "TEST-MARKET",
        status: str = "active",
        yes_bid: int = 45,
        yes_ask: int = 47,
        **overrides: Any,
    ) -> dict[str, Any]:
        base: dict[str, Any] = dict(market_template)
        base.update(
            {
                "ticker": ticker,
                "event_ticker": "TEST-EVENT",
                "series_ticker": "TEST",
                "title": f"Test Market {ticker}",
                "subtitle": "",
                "status": status,
                "result": "",
                "yes_bid": yes_bid,
                "yes_ask": yes_ask,
                "volume": 10000,
                "volume_24h": 1000,
                "open_interest": 5000,
                "created_time": "2023-12-15T17:50:26Z",
                "open_time": "2024-01-01T00:00:00Z",
                "close_time": "2025-12-31T00:00:00Z",
                "expiration_time": "2026-01-01T00:00:00Z",
            }
        )
        base.update(overrides)

        final_yes_bid = base.get("yes_bid")
        final_yes_ask = base.get("yes_ask")
        if isinstance(final_yes_bid, int) and isinstance(final_yes_ask, int):
            base["no_bid"] = 100 - final_yes_ask
            base["no_ask"] = 100 - final_yes_bid
            base["last_price"] = (final_yes_bid + final_yes_ask) // 2

            base["yes_bid_dollars"] = _cents_to_fixed_dollars(final_yes_bid)
            base["yes_ask_dollars"] = _cents_to_fixed_dollars(final_yes_ask)
            base["no_bid_dollars"] = _cents_to_fixed_dollars(100 - final_yes_ask)
            base["no_ask_dollars"] = _cents_to_fixed_dollars(100 - final_yes_bid)
            base["last_price_dollars"] = _cents_to_fixed_dollars(base["last_price"])
        return base

    return _make


@pytest.fixture
def make_orderbook() -> Callable[..., dict[str, list[list[int]]]]:
    """Factory to create REAL Orderbook objects."""

    def _make(
        yes_bids: list[tuple[int, int]] | None = None,
        no_bids: list[tuple[int, int]] | None = None,
    ) -> dict[str, list[list[int]]]:
        # After Phase 2: return Orderbook(yes=yes_bids, no=no_bids)
        return {
            "yes": [list(t) for t in (yes_bids or [(45, 100), (44, 200), (43, 500)])],
            "no": [list(t) for t in (no_bids or [(53, 150), (54, 250), (55, 400)])],
        }

    return _make


@pytest.fixture
def make_trade() -> Callable[..., dict[str, Any]]:
    """Factory to create REAL Trade objects."""

    def _make(
        ticker: str = "TEST-MARKET",
        yes_price: int = 46,
        count: int = 10,
        taker_side: str = "yes",
        **overrides: Any,
    ) -> dict[str, Any]:
        base: dict[str, Any] = {
            "trade_id": f"trade-{ticker}-{yes_price}",
            "ticker": ticker,
            "created_time": datetime.now(UTC).isoformat(),
            "yes_price": yes_price,
            "no_price": 100 - yes_price,
            "count": count,
            "taker_side": taker_side,
        }
        base.update(overrides)
        return base

    return _make


# ============================================================================
# Time Injection (for testability without mocking)
# ============================================================================
class FixedClock:
    """A clock that always returns a fixed time."""

    def __init__(self, fixed_time: datetime) -> None:
        self.time = fixed_time

    def __call__(self) -> datetime:
        return self.time


@pytest.fixture
def fixed_clock() -> FixedClock:
    """Returns a clock function that always returns the same time."""
    fixed_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    return FixedClock(fixed_time)
