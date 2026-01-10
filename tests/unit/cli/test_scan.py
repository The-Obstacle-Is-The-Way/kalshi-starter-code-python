from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from kalshi_research.api.models.market import Market
from kalshi_research.api.models.orderbook import Orderbook
from kalshi_research.cli import app

if TYPE_CHECKING:
    from collections.abc import Callable

runner = CliRunner()


@patch("kalshi_research.data.repositories.PriceRepository")
@patch("kalshi_research.data.DatabaseManager")
@patch("kalshi_research.api.KalshiPublicClient")
def test_scan_movers_uses_probability_units(
    mock_client_cls: MagicMock,
    mock_db_cls: MagicMock,
    mock_price_repo_cls: MagicMock,
) -> None:
    from datetime import UTC, datetime, timedelta

    from kalshi_research.data.models import PriceSnapshot

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    mock_market = MagicMock()
    mock_market.ticker = "TEST-TICKER"
    mock_market.title = "Test Market"
    mock_market.volume = 1000

    async def market_gen(status=None, max_pages: int | None = None):
        yield mock_market

    mock_client.get_all_markets = MagicMock(side_effect=market_gen)

    now = datetime.now(UTC)
    newest = PriceSnapshot(
        ticker="TEST-TICKER",
        snapshot_time=now,
        yes_bid=51,
        yes_ask=53,
        no_bid=47,
        no_ask=49,
        last_price=52,
        volume=100,
        volume_24h=10,
        open_interest=20,
        liquidity=1000,
    )
    oldest = PriceSnapshot(
        ticker="TEST-TICKER",
        snapshot_time=now - timedelta(hours=1),
        yes_bid=49,
        yes_ask=51,
        no_bid=49,
        no_ask=51,
        last_price=50,
        volume=100,
        volume_24h=10,
        open_interest=20,
        liquidity=1000,
    )

    mock_price_repo = MagicMock()
    mock_price_repo.get_for_market = AsyncMock(return_value=[newest, oldest])
    mock_price_repo_cls.return_value = mock_price_repo

    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session_cm
    mock_session_cm.__aexit__.return_value = False

    mock_db_cm = AsyncMock()
    mock_db_cm.__aenter__.return_value = mock_db_cm
    mock_db_cm.__aexit__.return_value = False
    mock_db_cm.session_factory = MagicMock(return_value=mock_session_cm)
    mock_db_cls.return_value = mock_db_cm

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["scan", "movers", "--period", "24h", "--top", "1"])

    assert result.exit_code == 0
    assert "50.0% → 52.0%" in result.stdout
    assert "2.0%" in result.stdout


@patch("kalshi_research.data.repositories.PriceRepository")
@patch("kalshi_research.data.DatabaseManager")
@patch("kalshi_research.api.KalshiPublicClient")
def test_scan_arbitrage_warns_when_tickers_truncated(
    mock_client_cls: MagicMock,
    mock_db_cls: MagicMock,
    mock_price_repo_cls: MagicMock,
) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    m1 = MagicMock()
    m1.ticker = "T1"
    m1.event_ticker = "E1"
    m1.title = "Market 1"
    m1.yes_bid = 50
    m1.yes_ask = 52

    m2 = MagicMock()
    m2.ticker = "T2"
    m2.event_ticker = "E2"
    m2.title = "Market 2"
    m2.yes_bid = 48
    m2.yes_ask = 50

    async def market_gen(status=None, max_pages: int | None = None):
        yield m1
        yield m2

    mock_client.get_all_markets = MagicMock(side_effect=market_gen)

    mock_price_repo = MagicMock()
    mock_price_repo.get_for_market = AsyncMock(return_value=[])
    mock_price_repo_cls.return_value = mock_price_repo

    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session_cm
    mock_session_cm.__aexit__.return_value = False

    mock_db_cm = AsyncMock()
    mock_db_cm.__aenter__.return_value = mock_db_cm
    mock_db_cm.__aexit__.return_value = False
    mock_db_cm.session_factory = MagicMock(return_value=mock_session_cm)
    mock_db_cls.return_value = mock_db_cm

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["scan", "arbitrage", "--tickers-limit", "1"])

    assert result.exit_code == 0
    assert "Limiting correlation analysis to first 1 tickers" in result.stdout


@patch("kalshi_research.api.KalshiPublicClient")
def test_scan_opportunities_does_not_fetch_orderbooks_by_default(
    mock_client_cls: MagicMock,
    make_market: Callable[..., dict[str, object]],
) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    high_liquidity = Market.model_validate(
        make_market(
            ticker="HIGH-LIQ",
            yes_bid=50,
            yes_ask=51,
            volume_24h=10_000,
            open_interest=5_000,
            close_time="2099-12-31T00:00:00Z",
            expiration_time="2100-01-01T00:00:00Z",
        )
    )
    low_liquidity = Market.model_validate(
        make_market(
            ticker="LOW-LIQ",
            yes_bid=50,
            yes_ask=51,
            volume_24h=0,
            open_interest=0,
            close_time="2099-12-31T00:00:00Z",
            expiration_time="2100-01-01T00:00:00Z",
        )
    )

    async def market_gen(*, status: str | None = None, max_pages: int | None = None):
        _ = status, max_pages
        yield high_liquidity
        yield low_liquidity

    mock_client.get_all_markets = MagicMock(side_effect=market_gen)
    mock_client.get_orderbook = AsyncMock()

    result = runner.invoke(app, ["scan", "opportunities", "--filter", "close-race", "--top", "2"])

    assert result.exit_code == 0
    assert "HIGH-LIQ" in result.stdout
    assert "LOW-LIQ" in result.stdout
    assert "Liquidity" not in result.stdout
    mock_client.get_orderbook.assert_not_awaited()


@patch("kalshi_research.api.KalshiPublicClient")
def test_scan_opportunities_show_liquidity_fetches_orderbooks_with_depth(
    mock_client_cls: MagicMock,
    make_market: Callable[..., dict[str, object]],
) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    high_liquidity = Market.model_validate(
        make_market(
            ticker="HIGH-LIQ",
            yes_bid=50,
            yes_ask=51,
            volume_24h=10_000,
            open_interest=5_000,
            close_time="2099-12-31T00:00:00Z",
            expiration_time="2100-01-01T00:00:00Z",
        )
    )
    low_liquidity = Market.model_validate(
        make_market(
            ticker="LOW-LIQ",
            yes_bid=50,
            yes_ask=51,
            volume_24h=0,
            open_interest=0,
            close_time="2099-12-31T00:00:00Z",
            expiration_time="2100-01-01T00:00:00Z",
        )
    )

    async def market_gen(*, status: str | None = None, max_pages: int | None = None):
        _ = status, max_pages
        yield high_liquidity
        yield low_liquidity

    async def orderbook_for_ticker(ticker: str, *, depth: int):
        _ = depth
        if ticker == "HIGH-LIQ":
            return Orderbook(yes=[(50, 5_000)], no=[(49, 5_000)])
        return Orderbook(yes=None, no=None)

    mock_client.get_all_markets = MagicMock(side_effect=market_gen)
    mock_client.get_orderbook = AsyncMock(side_effect=orderbook_for_ticker)

    result = runner.invoke(
        app,
        [
            "scan",
            "opportunities",
            "--filter",
            "close-race",
            "--top",
            "2",
            "--show-liquidity",
            "--liquidity-depth",
            "7",
        ],
    )

    assert result.exit_code == 0
    assert "Liquidity" in result.stdout
    assert "HIGH-LIQ" in result.stdout
    assert "LOW-LIQ" in result.stdout
    assert "100" in result.stdout
    mock_client.get_orderbook.assert_any_await("HIGH-LIQ", depth=7)
    mock_client.get_orderbook.assert_any_await("LOW-LIQ", depth=7)


@patch("kalshi_research.api.KalshiPublicClient")
def test_scan_opportunities_min_liquidity_filters_results(
    mock_client_cls: MagicMock,
    make_market: Callable[..., dict[str, object]],
) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client_cls.return_value = mock_client

    high_liquidity = Market.model_validate(
        make_market(
            ticker="HIGH-LIQ",
            yes_bid=50,
            yes_ask=51,
            volume_24h=10_000,
            open_interest=5_000,
            close_time="2099-12-31T00:00:00Z",
            expiration_time="2100-01-01T00:00:00Z",
        )
    )
    low_liquidity = Market.model_validate(
        make_market(
            ticker="LOW-LIQ",
            yes_bid=50,
            yes_ask=51,
            volume_24h=0,
            open_interest=0,
            close_time="2099-12-31T00:00:00Z",
            expiration_time="2100-01-01T00:00:00Z",
        )
    )

    async def market_gen(*, status: str | None = None, max_pages: int | None = None):
        _ = status, max_pages
        yield high_liquidity
        yield low_liquidity

    async def orderbook_for_ticker(ticker: str, *, depth: int):
        _ = depth
        if ticker == "HIGH-LIQ":
            return Orderbook(yes=[(50, 5_000)], no=[(49, 5_000)])
        return Orderbook(yes=None, no=None)

    mock_client.get_all_markets = MagicMock(side_effect=market_gen)
    mock_client.get_orderbook = AsyncMock(side_effect=orderbook_for_ticker)

    result = runner.invoke(
        app,
        [
            "scan",
            "opportunities",
            "--filter",
            "close-race",
            "--top",
            "2",
            "--min-liquidity",
            "50",
        ],
    )

    assert result.exit_code == 0
    assert "HIGH-LIQ" in result.stdout
    assert "LOW-LIQ" not in result.stdout
    assert "Liquidity" in result.stdout
    mock_client.get_orderbook.assert_any_await("HIGH-LIQ", depth=25)
    mock_client.get_orderbook.assert_any_await("LOW-LIQ", depth=25)
