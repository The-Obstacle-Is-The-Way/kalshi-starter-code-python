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

    high_orderbook = {"yes": [[50, 5_000]], "no": [[49, 5_000]]}
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

    high_orderbook = {"yes": [[50, 5_000]], "no": [[49, 5_000]]}
    low_orderbook = {"yes": None, "no": None}

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
    "kalshi_research.analysis.correlation.CorrelationAnalyzer.find_inverse_markets",
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
