from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import respx
from httpx import Response
from typer.testing import CliRunner

from kalshi_research.api.models.market import Market
from kalshi_research.api.models.orderbook import Orderbook
from kalshi_research.cli import app
from tests.unit.cli.fixtures import KALSHI_PROD_BASE_URL, load_events_list_fixture

if TYPE_CHECKING:
    from collections.abc import Callable

runner = CliRunner()


@patch("kalshi_research.data.repositories.PriceRepository")
@patch("kalshi_research.data.DatabaseManager")
def test_scan_movers_uses_probability_units(
    mock_db_cls: MagicMock,
    mock_price_repo_cls: MagicMock,
    make_market: Callable[..., dict[str, object]],
) -> None:
    from datetime import UTC, datetime, timedelta

    from kalshi_research.data.models import PriceSnapshot

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

    market = make_market(ticker="TEST-TICKER", title="Test Market", volume=1000)
    markets_response = {"markets": [market], "cursor": None}

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/markets").mock(
            return_value=Response(200, json=markets_response)
        )
        with patch("pathlib.Path.exists", return_value=True):
            result = runner.invoke(app, ["scan", "movers", "--period", "24h", "--top", "1"])

    assert result.exit_code == 0
    assert "50.0% → 52.0%" in result.stdout
    assert "2.0%" in result.stdout


@patch("kalshi_research.data.repositories.PriceRepository")
@patch("kalshi_research.data.DatabaseManager")
def test_scan_movers_full_flag_disables_title_truncation(
    mock_db_cls: MagicMock,
    mock_price_repo_cls: MagicMock,
    make_market: Callable[..., dict[str, object]],
) -> None:
    from datetime import UTC, datetime, timedelta

    from kalshi_research.data.models import PriceSnapshot

    title_suffix = "TAILTITLE"
    long_title = f"{'A' * 55}{title_suffix}"

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

    market = make_market(ticker="TEST-TICKER", title=long_title, volume=1000)
    markets_response = {"markets": [market], "cursor": None}

    with respx.mock:
        route = respx.get(f"{KALSHI_PROD_BASE_URL}/markets")
        route.side_effect = [
            Response(200, json=markets_response),
            Response(200, json=markets_response),
        ]

        with patch("pathlib.Path.exists", return_value=True):
            result_default = runner.invoke(app, ["scan", "movers", "--period", "24h", "--top", "1"])
        with patch("pathlib.Path.exists", return_value=True):
            result_full = runner.invoke(
                app,
                ["scan", "movers", "--period", "24h", "--top", "1", "--full"],
            )

    assert result_default.exit_code == 0
    assert title_suffix not in result_default.stdout

    assert result_full.exit_code == 0
    assert title_suffix in result_full.stdout


@patch("kalshi_research.data.repositories.PriceRepository")
@patch("kalshi_research.data.DatabaseManager")
def test_scan_arbitrage_warns_when_tickers_truncated(
    mock_db_cls: MagicMock,
    mock_price_repo_cls: MagicMock,
    make_market: Callable[..., dict[str, object]],
) -> None:
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

    markets = [
        make_market(ticker="T1", title="Market 1", yes_bid=50, yes_ask=52),
        make_market(ticker="T2", title="Market 2", yes_bid=48, yes_ask=50),
    ]
    markets_response = {"markets": markets, "cursor": None}

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/markets").mock(
            return_value=Response(200, json=markets_response)
        )
        with patch("pathlib.Path.exists", return_value=True):
            result = runner.invoke(app, ["scan", "arbitrage", "--tickers-limit", "1"])

    assert result.exit_code == 0
    assert "Limiting correlation analysis to first 1 tickers" in result.stdout


def test_scan_opportunities_does_not_fetch_orderbooks_by_default(
    make_market: Callable[..., dict[str, object]],
) -> None:
    high_liquidity = make_market(
        ticker="HIGH-LIQ",
        yes_bid=50,
        yes_ask=51,
        volume_24h=10_000,
        open_interest=5_000,
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    low_liquidity = make_market(
        ticker="LOW-LIQ",
        yes_bid=50,
        yes_ask=51,
        volume_24h=0,
        open_interest=0,
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )

    markets_response = {"markets": [high_liquidity, low_liquidity], "cursor": None}

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/exchange/status").mock(
            return_value=Response(200, json={"exchange_active": True, "trading_active": True})
        )
        respx.get(f"{KALSHI_PROD_BASE_URL}/markets").mock(
            return_value=Response(200, json=markets_response)
        )

        result = runner.invoke(
            app, ["scan", "opportunities", "--filter", "close-race", "--top", "2"]
        )

    assert result.exit_code == 0
    assert "HIGH-LIQ" in result.stdout
    assert "LOW-LIQ" in result.stdout
    assert "Liquidity" not in result.stdout


def test_scan_opportunities_show_liquidity_fetches_orderbooks_with_depth(
    make_market: Callable[..., dict[str, object]],
) -> None:
    from kalshi_research.analysis.liquidity import liquidity_score

    high_liquidity = make_market(
        ticker="HIGH-LIQ",
        yes_bid=50,
        yes_ask=51,
        volume_24h=10_000,
        open_interest=5_000,
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    low_liquidity = make_market(
        ticker="LOW-LIQ",
        yes_bid=50,
        yes_ask=51,
        volume_24h=0,
        open_interest=0,
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    markets_response = {"markets": [high_liquidity, low_liquidity], "cursor": None}

    high_orderbook = {
        "yes": [[50, 5_000]],
        "no": [[49, 5_000]],
        "yes_dollars": [["0.50", 5_000]],
        "no_dollars": [["0.49", 5_000]],
    }
    low_orderbook = {"yes": None, "no": None}

    expected_score = liquidity_score(
        Market.model_validate(high_liquidity),
        Orderbook.model_validate(high_orderbook),
    ).score

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/exchange/status").mock(
            return_value=Response(200, json={"exchange_active": True, "trading_active": True})
        )
        respx.get(f"{KALSHI_PROD_BASE_URL}/markets").mock(
            return_value=Response(200, json=markets_response)
        )
        high_route = respx.get(f"{KALSHI_PROD_BASE_URL}/markets/HIGH-LIQ/orderbook").mock(
            return_value=Response(200, json={"orderbook": high_orderbook})
        )
        low_route = respx.get(f"{KALSHI_PROD_BASE_URL}/markets/LOW-LIQ/orderbook").mock(
            return_value=Response(200, json={"orderbook": low_orderbook})
        )

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
    assert str(expected_score) in result.stdout
    assert high_route.calls[0].request.url.params["depth"] == "7"
    assert low_route.calls[0].request.url.params["depth"] == "7"


def test_scan_opportunities_min_liquidity_filters_results(
    make_market: Callable[..., dict[str, object]],
) -> None:
    high_liquidity = make_market(
        ticker="HIGH-LIQ",
        yes_bid=50,
        yes_ask=51,
        volume_24h=10_000,
        open_interest=5_000,
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    low_liquidity = make_market(
        ticker="LOW-LIQ",
        yes_bid=50,
        yes_ask=51,
        volume_24h=0,
        open_interest=0,
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    markets_response = {"markets": [high_liquidity, low_liquidity], "cursor": None}

    high_orderbook = {
        "yes": [[50, 5_000]],
        "no": [[49, 5_000]],
        "yes_dollars": [["0.50", 5_000]],
        "no_dollars": [["0.49", 5_000]],
    }
    low_orderbook = {"yes": None, "no": None, "yes_dollars": None, "no_dollars": None}

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/exchange/status").mock(
            return_value=Response(200, json={"exchange_active": True, "trading_active": True})
        )
        respx.get(f"{KALSHI_PROD_BASE_URL}/markets").mock(
            return_value=Response(200, json=markets_response)
        )
        high_route = respx.get(f"{KALSHI_PROD_BASE_URL}/markets/HIGH-LIQ/orderbook").mock(
            return_value=Response(200, json={"orderbook": high_orderbook})
        )
        low_route = respx.get(f"{KALSHI_PROD_BASE_URL}/markets/LOW-LIQ/orderbook").mock(
            return_value=Response(200, json={"orderbook": low_orderbook})
        )

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
    assert high_route.calls[0].request.url.params["depth"] == "25"
    assert low_route.calls[0].request.url.params["depth"] == "25"


def test_scan_opportunities_parses_exchange_status_booleans(
    make_market: Callable[..., dict[str, object]],
) -> None:
    market = make_market(
        ticker="HIGH-LIQ",
        yes_bid=50,
        yes_ask=51,
        volume_24h=10_000,
        open_interest=5_000,
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    markets_response = {"markets": [market], "cursor": None}

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/exchange/status").mock(
            return_value=Response(200, json={"exchange_active": True, "trading_active": True})
        )
        respx.get(f"{KALSHI_PROD_BASE_URL}/markets").mock(
            return_value=Response(200, json=markets_response)
        )

        result = runner.invoke(
            app, ["scan", "opportunities", "--filter", "close-race", "--top", "1"]
        )

    assert result.exit_code == 0
    assert "Warning:" not in result.stdout


def test_scan_opportunities_warns_when_exchange_status_missing_boolean_fields(
    make_market: Callable[..., dict[str, object]],
) -> None:
    market = make_market(
        ticker="HIGH-LIQ",
        yes_bid=50,
        yes_ask=51,
        volume_24h=10_000,
        open_interest=5_000,
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    markets_response = {"markets": [market], "cursor": None}

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/exchange/status").mock(
            return_value=Response(200, json={"exchange_active": "yes", "trading_active": True})
        )
        respx.get(f"{KALSHI_PROD_BASE_URL}/markets").mock(
            return_value=Response(200, json=markets_response)
        )

        result = runner.invoke(
            app, ["scan", "opportunities", "--filter", "close-race", "--top", "1"]
        )

    assert result.exit_code == 0
    assert "Exchange status response was missing expected boolean fields" in result.stdout


def test_scan_opportunities_no_sports_excludes_sports_markets(
    make_market: Callable[..., dict[str, object]],
) -> None:
    econ_market = make_market(
        ticker="ECON-MARKET",
        event_ticker="KXFEDRATE-26JAN",
        yes_bid=50,
        yes_ask=51,
        volume_24h=10_000,
        open_interest=5_000,
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    sports_market = make_market(
        ticker="SPORTS-MARKET",
        event_ticker="KXNFLAFCCHAMP-26JAN",
        yes_bid=50,
        yes_ask=51,
        volume_24h=10_000,
        open_interest=5_000,
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )

    template = load_events_list_fixture()["events"][0]

    econ_event = dict(template)
    econ_event.update(
        {
            "event_ticker": econ_market["event_ticker"],
            "category": "Economics",
            "markets": [econ_market],
        }
    )
    sports_event = dict(template)
    sports_event.update(
        {
            "event_ticker": sports_market["event_ticker"],
            "category": "Sports",
            "markets": [sports_market],
        }
    )

    response = {"events": [econ_event, sports_event], "cursor": None}

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/exchange/status").mock(
            return_value=Response(200, json={"exchange_active": True, "trading_active": True})
        )
        respx.get(f"{KALSHI_PROD_BASE_URL}/events").mock(return_value=Response(200, json=response))

        result = runner.invoke(
            app,
            [
                "scan",
                "opportunities",
                "--filter",
                "close-race",
                "--top",
                "2",
                "--no-sports",
            ],
        )

    assert result.exit_code == 0
    assert "ECON-MARKET" in result.stdout
    assert "SPORTS-MARKET" not in result.stdout


def test_scan_opportunities_category_filters_markets(
    make_market: Callable[..., dict[str, object]],
) -> None:
    econ_market = make_market(
        ticker="ECON-MARKET",
        event_ticker="KXFEDRATE-26JAN",
        yes_bid=50,
        yes_ask=51,
        volume_24h=10_000,
        open_interest=5_000,
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    sports_market = make_market(
        ticker="SPORTS-MARKET",
        event_ticker="KXNFLAFCCHAMP-26JAN",
        yes_bid=50,
        yes_ask=51,
        volume_24h=10_000,
        open_interest=5_000,
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )

    template = load_events_list_fixture()["events"][0]
    econ_event = dict(template)
    econ_event.update(
        {
            "event_ticker": econ_market["event_ticker"],
            "category": "Economics",
            "markets": [econ_market],
        }
    )
    sports_event = dict(template)
    sports_event.update(
        {
            "event_ticker": sports_market["event_ticker"],
            "category": "Sports",
            "markets": [sports_market],
        }
    )
    response = {"events": [econ_event, sports_event], "cursor": None}

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/exchange/status").mock(
            return_value=Response(200, json={"exchange_active": True, "trading_active": True})
        )
        respx.get(f"{KALSHI_PROD_BASE_URL}/events").mock(return_value=Response(200, json=response))

        result = runner.invoke(
            app,
            [
                "scan",
                "opportunities",
                "--filter",
                "close-race",
                "--top",
                "2",
                "--category",
                "econ",
            ],
        )

    assert result.exit_code == 0
    assert "ECON-MARKET" in result.stdout
    assert "SPORTS-MARKET" not in result.stdout


def test_scan_opportunities_full_flag_disables_title_truncation(
    make_market: Callable[..., dict[str, object]],
) -> None:
    title_suffix = "TAILTITLE"
    long_title = f"{'A' * 60}{title_suffix}"

    market = make_market(
        ticker="LONG-TITLE",
        title=long_title,
        yes_bid=50,
        yes_ask=51,
        volume_24h=10_000,
        open_interest=5_000,
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    markets_response = {"markets": [market], "cursor": None}

    with respx.mock:
        exchange_route = respx.get(f"{KALSHI_PROD_BASE_URL}/exchange/status")
        exchange_route.side_effect = [
            Response(200, json={"exchange_active": True, "trading_active": True}),
            Response(200, json={"exchange_active": True, "trading_active": True}),
        ]

        markets_route = respx.get(f"{KALSHI_PROD_BASE_URL}/markets")
        markets_route.side_effect = [
            Response(200, json=markets_response),
            Response(200, json=markets_response),
        ]

        result_default = runner.invoke(
            app,
            [
                "scan",
                "opportunities",
                "--filter",
                "close-race",
                "--top",
                "1",
            ],
        )
        result_full = runner.invoke(
            app,
            [
                "scan",
                "opportunities",
                "--filter",
                "close-race",
                "--top",
                "1",
                "--full",
            ],
        )

    assert result_default.exit_code == 0
    assert title_suffix not in result_default.stdout

    assert result_full.exit_code == 0
    assert title_suffix in result_full.stdout


def test_scan_opportunities_propagates_cancelled_error() -> None:
    with (
        patch(
            "kalshi_research.api.client.KalshiPublicClient.get_exchange_status",
            new=AsyncMock(side_effect=asyncio.CancelledError()),
        ),
        pytest.raises(asyncio.CancelledError),
    ):
        runner.invoke(app, ["scan", "opportunities", "--filter", "close-race", "--top", "1"])


@patch(
    "kalshi_research.analysis.correlation.CorrelationAnalyzer.find_inverse_market_groups",
    return_value=[],
)
@patch(
    "kalshi_research.analysis.correlation.CorrelationAnalyzer.find_arbitrage_opportunities",
)
def test_scan_arbitrage_full_flag_disables_truncation(
    mock_find_arbs: MagicMock,
    _mock_find_inverse: MagicMock,
    make_market: Callable[..., dict[str, object]],
) -> None:
    from kalshi_research.analysis.correlation import ArbitrageOpportunity

    markets = [
        make_market(ticker="T1", title="Market 1", yes_bid=50, yes_ask=52),
        make_market(ticker="T2", title="Market 2", yes_bid=48, yes_ask=50),
    ]
    markets_response = {"markets": markets, "cursor": None}

    ticker_suffix = "TAILTICKER"
    expected_suffix = "TAILEXPECTED"
    opportunity = ArbitrageOpportunity(
        tickers=[f"{'A' * 35}", f"{'B' * 20}{ticker_suffix}"],
        opportunity_type="divergence",
        expected_relationship=f"{'X' * 55}{expected_suffix}",
        actual_values={"T1": 0.5, "T2": 0.4},
        divergence=0.2,
        confidence=0.95,
    )
    mock_find_arbs.return_value = [opportunity]

    with respx.mock:
        route = respx.get(f"{KALSHI_PROD_BASE_URL}/markets")
        route.side_effect = [
            Response(200, json=markets_response),
            Response(200, json=markets_response),
        ]

        with patch("pathlib.Path.exists", return_value=False):
            result_default = runner.invoke(app, ["scan", "arbitrage", "--top", "1"])
            assert result_default.exit_code == 0
            assert ticker_suffix not in result_default.stdout
            assert expected_suffix not in result_default.stdout

        with patch("pathlib.Path.exists", return_value=False):
            result_full = runner.invoke(app, ["scan", "arbitrage", "--top", "1", "--full"])
            assert result_full.exit_code == 0
            assert ticker_suffix in result_full.stdout
            assert expected_suffix in result_full.stdout


def test_market_yes_price_display_shows_half_cent_midpoints() -> None:
    from datetime import UTC, datetime

    from kalshi_research.api.models import Market, MarketStatus
    from kalshi_research.cli.scan import _market_yes_price_display

    market = Market(
        ticker="TEST",
        event_ticker="EVT",
        title="Test",
        status=MarketStatus.ACTIVE,
        yes_bid=49,
        yes_ask=50,
        yes_bid_dollars="0.49",
        yes_ask_dollars="0.50",
        no_bid=50,
        no_ask=51,
        no_bid_dollars="0.50",
        no_ask_dollars="0.51",
        last_price=49,
        last_price_dollars="0.49",
        volume=0,
        volume_24h=0,
        open_interest=0,
        open_time=datetime(2024, 1, 1, tzinfo=UTC),
        close_time=datetime(2025, 1, 1, tzinfo=UTC),
        expiration_time=datetime(2025, 1, 2, tzinfo=UTC),
    )

    assert _market_yes_price_display(market) == "49.5¢"


def test_market_yes_price_display_shows_no_quotes_when_zero_zero() -> None:
    from datetime import UTC, datetime

    from kalshi_research.api.models import Market, MarketStatus
    from kalshi_research.cli.scan import _market_yes_price_display

    market = Market(
        ticker="TEST",
        event_ticker="EVT",
        title="Test",
        status=MarketStatus.ACTIVE,
        yes_bid=0,
        yes_ask=0,
        yes_bid_dollars="0.00",
        yes_ask_dollars="0.00",
        no_bid=0,
        no_ask=0,
        no_bid_dollars="0.00",
        no_ask_dollars="0.00",
        last_price=None,
        volume=0,
        volume_24h=0,
        open_interest=0,
        open_time=datetime(2024, 1, 1, tzinfo=UTC),
        close_time=datetime(2025, 1, 1, tzinfo=UTC),
        expiration_time=datetime(2025, 1, 2, tzinfo=UTC),
    )

    assert _market_yes_price_display(market) == "[NO QUOTES]"


def test_format_relative_age_supports_seconds_minutes_hours_days_and_future() -> None:
    from datetime import UTC, datetime, timedelta

    from kalshi_research.cli.scan import _format_relative_age

    now = datetime(2026, 1, 1, tzinfo=UTC)

    assert _format_relative_age(now=now, timestamp=now - timedelta(seconds=30)) == "30s ago"
    assert _format_relative_age(now=now, timestamp=now - timedelta(minutes=5)) == "5m ago"
    assert _format_relative_age(now=now, timestamp=now - timedelta(hours=2)) == "2h ago"
    assert _format_relative_age(now=now, timestamp=now - timedelta(days=3)) == "3d ago"
    assert _format_relative_age(now=now, timestamp=now + timedelta(minutes=2)) == "in 2m"


def test_parse_category_filter_returns_none_when_only_commas_and_spaces() -> None:
    from kalshi_research.cli.scan import _parse_category_filter

    assert _parse_category_filter(" , , ") is None


def test_validate_new_markets_args_requires_positive_hours_and_limit() -> None:
    import typer

    from kalshi_research.cli.scan import _validate_new_markets_args

    with pytest.raises(typer.Exit) as excinfo:
        _validate_new_markets_args(hours=0, limit=10)
    assert excinfo.value.exit_code == 1

    with pytest.raises(typer.Exit) as excinfo:
        _validate_new_markets_args(hours=24, limit=0)
    assert excinfo.value.exit_code == 1


@pytest.mark.asyncio
async def test_get_event_category_returns_cached_value() -> None:
    from kalshi_research.cli.scan import _get_event_category

    category_by_event = {"EVT": "Economics"}
    category = await _get_event_category(MagicMock(), "EVT", category_by_event=category_by_event)

    assert category == "Economics"


@pytest.mark.asyncio
async def test_get_event_category_falls_back_when_event_has_no_category() -> None:
    from kalshi_research.api.models.event import Event
    from kalshi_research.cli.scan import _get_event_category

    client = AsyncMock()
    client.get_event = AsyncMock(
        return_value=Event(
            event_ticker="KXFED-TEST",
            series_ticker="SERIES",
            title="Test",
            category=None,
        )
    )

    category = await _get_event_category(client, "KXFED-TEST", category_by_event={})
    assert category == "Economics"


@pytest.mark.asyncio
async def test_get_event_category_falls_back_on_api_error() -> None:
    from kalshi_research.api.exceptions import KalshiAPIError
    from kalshi_research.cli.scan import _get_event_category

    client = AsyncMock()
    client.get_event = AsyncMock(side_effect=KalshiAPIError(500, "boom"))

    category = await _get_event_category(client, "KXFED-TEST", category_by_event={})
    assert category == "Economics"


def test_format_opportunity_tickers() -> None:
    from kalshi_research.cli.scan import _format_opportunity_tickers

    assert _format_opportunity_tickers(["A", "B"], full=False) == "A, B"
    assert _format_opportunity_tickers(["A", "B", "C"], full=False) == "A, B, +1"
    assert _format_opportunity_tickers(["A", "B", "C"], full=True) == "A, B, C"


def test_scan_new_markets_filters_by_created_time(
    make_market: Callable[..., dict[str, object]],
) -> None:
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    new_market = make_market(
        ticker="NEW-MARKET",
        event_ticker="EVT-NEW",
        created_time=(now - timedelta(hours=1)).isoformat(),
        open_time=(now - timedelta(hours=1)).isoformat(),
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    old_market = make_market(
        ticker="OLD-MARKET",
        event_ticker="EVT-OLD",
        created_time=(now - timedelta(hours=30)).isoformat(),
        open_time=(now - timedelta(hours=30)).isoformat(),
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    markets_response = {"markets": [new_market, old_market], "cursor": None}

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/markets").mock(
            return_value=Response(200, json=markets_response)
        )
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/EVT-NEW").mock(
            return_value=Response(
                200,
                json={
                    "event": {
                        "event_ticker": "EVT-NEW",
                        "series_ticker": "SERIES",
                        "title": "Event NEW",
                        "category": "Economics",
                    }
                },
            )
        )

        result = runner.invoke(app, ["scan", "new-markets", "--hours", "24", "--limit", "10"])

    assert result.exit_code == 0
    assert "NEW-MARKET" in result.stdout
    assert "OLD-MARKET" not in result.stdout
    assert "Economics" in result.stdout


def test_scan_new_markets_respects_limit(make_market: Callable[..., dict[str, object]]) -> None:
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    newest = make_market(
        ticker="NEWEST",
        event_ticker="EVT-NEWEST",
        created_time=(now - timedelta(hours=1)).isoformat(),
        open_time=(now - timedelta(hours=1)).isoformat(),
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    older = make_market(
        ticker="OLDER",
        event_ticker="EVT-OLDER",
        created_time=(now - timedelta(hours=2)).isoformat(),
        open_time=(now - timedelta(hours=2)).isoformat(),
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    markets_response = {"markets": [newest, older], "cursor": None}

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/markets").mock(
            return_value=Response(200, json=markets_response)
        )
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/EVT-NEWEST").mock(
            return_value=Response(
                200,
                json={
                    "event": {
                        "event_ticker": "EVT-NEWEST",
                        "series_ticker": "SERIES",
                        "title": "Event NEWEST",
                        "category": "Economics",
                    }
                },
            )
        )

        result = runner.invoke(app, ["scan", "new-markets", "--hours", "24", "--limit", "1"])

    assert result.exit_code == 0
    assert "NEWEST" in result.stdout
    assert "OLDER" not in result.stdout


def test_scan_new_markets_full_flag_disables_title_truncation(
    make_market: Callable[..., dict[str, object]],
) -> None:
    from datetime import UTC, datetime, timedelta

    title_suffix = "TAILTITLE"
    long_title = f"{'A' * 60}{title_suffix}"

    now = datetime.now(UTC)
    market = make_market(
        ticker="NEW-MARKET",
        title=long_title,
        event_ticker="EVT-NEW",
        created_time=(now - timedelta(hours=1)).isoformat(),
        open_time=(now - timedelta(hours=1)).isoformat(),
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    markets_response = {"markets": [market], "cursor": None}

    with respx.mock:
        route = respx.get(f"{KALSHI_PROD_BASE_URL}/markets")
        route.side_effect = [
            Response(200, json=markets_response),
            Response(200, json=markets_response),
        ]

        respx.get(f"{KALSHI_PROD_BASE_URL}/events/EVT-NEW").mock(
            return_value=Response(
                200,
                json={
                    "event": {
                        "event_ticker": "EVT-NEW",
                        "series_ticker": "SERIES",
                        "title": "Event NEW",
                        "category": "Economics",
                    }
                },
            )
        )

        result_default = runner.invoke(
            app, ["scan", "new-markets", "--hours", "24", "--limit", "10"]
        )
        result_full = runner.invoke(
            app,
            ["scan", "new-markets", "--hours", "24", "--limit", "10", "--full"],
        )

    assert result_default.exit_code == 0
    assert title_suffix not in result_default.stdout

    assert result_full.exit_code == 0
    assert title_suffix in result_full.stdout


def test_scan_new_markets_empty_results_json_payload() -> None:
    import json

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/markets").mock(
            return_value=Response(200, json={"markets": [], "cursor": None})
        )

        result = runner.invoke(
            app,
            ["scan", "new-markets", "--hours", "24", "--limit", "10", "--json"],
        )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["count"] == 0
    assert payload["markets"] == []


def test_scan_new_markets_empty_results_prints_message() -> None:
    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/markets").mock(
            return_value=Response(200, json={"markets": [], "cursor": None})
        )

        result = runner.invoke(app, ["scan", "new-markets", "--hours", "24", "--limit", "10"])

    assert result.exit_code == 0
    assert "No new markets found" in result.stdout


def test_scan_new_markets_json_output(
    make_market: Callable[..., dict[str, object]],
) -> None:
    import json
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    market = make_market(
        ticker="NEW-MARKET",
        event_ticker="EVT-NEW",
        created_time=(now - timedelta(hours=1)).isoformat(),
        open_time=(now - timedelta(hours=1)).isoformat(),
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    markets_response = {"markets": [market], "cursor": None}

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/markets").mock(
            return_value=Response(200, json=markets_response)
        )
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/EVT-NEW").mock(
            return_value=Response(
                200,
                json={
                    "event": {
                        "event_ticker": "EVT-NEW",
                        "series_ticker": "SERIES",
                        "title": "Event NEW",
                        "category": "Economics",
                    }
                },
            )
        )

        result = runner.invoke(
            app,
            ["scan", "new-markets", "--hours", "24", "--limit", "10", "--json"],
        )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["count"] == 1
    assert payload["markets"][0]["ticker"] == "NEW-MARKET"
    datetime.fromisoformat(payload["cutoff"])
    datetime.fromisoformat(payload["markets"][0]["created_time"])


def test_scan_new_markets_include_unpriced_flag_controls_placeholder_markets(
    make_market: Callable[..., dict[str, object]],
) -> None:
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    priced = make_market(
        ticker="PRICED",
        event_ticker="EVT-PRICED",
        yes_bid=50,
        yes_ask=52,
        created_time=(now - timedelta(hours=1)).isoformat(),
        open_time=(now - timedelta(hours=1)).isoformat(),
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    placeholder = make_market(
        ticker="PLACEHOLDER",
        event_ticker="EVT-PLACEHOLDER",
        yes_bid=0,
        yes_ask=100,
        created_time=(now - timedelta(hours=1)).isoformat(),
        open_time=(now - timedelta(hours=1)).isoformat(),
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    markets_response = {"markets": [priced, placeholder], "cursor": None}

    with respx.mock:
        route = respx.get(f"{KALSHI_PROD_BASE_URL}/markets")
        route.side_effect = [
            Response(200, json=markets_response),
            Response(200, json=markets_response),
        ]

        respx.get(f"{KALSHI_PROD_BASE_URL}/events/EVT-PRICED").mock(
            return_value=Response(
                200,
                json={
                    "event": {
                        "event_ticker": "EVT-PRICED",
                        "series_ticker": "SERIES",
                        "title": "Event PRICED",
                        "category": "Economics",
                    }
                },
            )
        )

        result_default = runner.invoke(
            app, ["scan", "new-markets", "--hours", "24", "--limit", "10"]
        )
        assert result_default.exit_code == 0
        assert "PRICED" in result_default.stdout
        assert "PLACEHOLDER" not in result_default.stdout
        assert "skipped 1 unpriced" in result_default.stdout

        respx.get(f"{KALSHI_PROD_BASE_URL}/events/EVT-PLACEHOLDER").mock(
            return_value=Response(
                200,
                json={
                    "event": {
                        "event_ticker": "EVT-PLACEHOLDER",
                        "series_ticker": "SERIES",
                        "title": "Event PLACEHOLDER",
                        "category": "Economics",
                    }
                },
            )
        )

        result_include = runner.invoke(
            app,
            [
                "scan",
                "new-markets",
                "--hours",
                "24",
                "--limit",
                "10",
                "--include-unpriced",
            ],
        )

    assert result_include.exit_code == 0
    assert "PRICED" in result_include.stdout
    assert "PLACEHOLDER" in result_include.stdout
    assert "AWAITING PRICE DISCOVERY" in result_include.stdout


def test_scan_new_markets_falls_back_to_open_time_with_warning(
    make_market: Callable[..., dict[str, object]],
) -> None:
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    market = make_market(
        ticker="NO-CREATED",
        event_ticker="EVT-NO-CREATED",
        created_time=None,
        open_time=(now - timedelta(hours=2)).isoformat(),
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    markets_response = {"markets": [market], "cursor": None}

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/markets").mock(
            return_value=Response(200, json=markets_response)
        )
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/EVT-NO-CREATED").mock(
            return_value=Response(
                200,
                json={
                    "event": {
                        "event_ticker": "EVT-NO-CREATED",
                        "series_ticker": "SERIES",
                        "title": "Event NO-CREATED",
                        "category": "Economics",
                    }
                },
            )
        )

        result = runner.invoke(app, ["scan", "new-markets", "--hours", "24", "--limit", "10"])

    assert result.exit_code == 0
    assert "Warning:" in result.stdout
    assert "missing created_time" in result.stdout
    assert "NO-CREATED" in result.stdout


def test_scan_new_markets_category_filter(
    make_market: Callable[..., dict[str, object]],
) -> None:
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    econ_market = make_market(
        ticker="ECON-NEW",
        event_ticker="EVT-ECON",
        created_time=(now - timedelta(hours=1)).isoformat(),
        open_time=(now - timedelta(hours=1)).isoformat(),
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    sports_market = make_market(
        ticker="SPORTS-NEW",
        event_ticker="EVT-SPORTS",
        created_time=(now - timedelta(hours=1)).isoformat(),
        open_time=(now - timedelta(hours=1)).isoformat(),
        close_time="2099-12-31T00:00:00Z",
        expiration_time="2100-01-01T00:00:00Z",
    )
    markets_response = {"markets": [econ_market, sports_market], "cursor": None}

    with respx.mock:
        respx.get(f"{KALSHI_PROD_BASE_URL}/markets").mock(
            return_value=Response(200, json=markets_response)
        )
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/EVT-ECON").mock(
            return_value=Response(
                200,
                json={
                    "event": {
                        "event_ticker": "EVT-ECON",
                        "series_ticker": "SERIES",
                        "title": "Event ECON",
                        "category": "Economics",
                    }
                },
            )
        )
        respx.get(f"{KALSHI_PROD_BASE_URL}/events/EVT-SPORTS").mock(
            return_value=Response(
                200,
                json={
                    "event": {
                        "event_ticker": "EVT-SPORTS",
                        "series_ticker": "SERIES",
                        "title": "Event SPORTS",
                        "category": "Sports",
                    }
                },
            )
        )

        result = runner.invoke(app, ["scan", "new-markets", "--category", "econ"])

    assert result.exit_code == 0
    assert "ECON-NEW" in result.stdout
    assert "SPORTS-NEW" not in result.stdout
