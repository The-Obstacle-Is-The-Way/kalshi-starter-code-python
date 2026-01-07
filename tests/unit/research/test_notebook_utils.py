"""Unit tests for notebook utilities."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from kalshi_research.analysis.edge import Edge, EdgeType
from kalshi_research.api.models import Event, Market
from kalshi_research.research.notebook_utils import (
    display_edge,
    display_market,
    display_markets_table,
    load_events,
    load_markets,
    run_async,
    setup_notebook,
)


class TestSetupNotebook:
    """Test setup_notebook function."""

    def test_setup_notebook_configures_pandas(self) -> None:
        """Test that setup_notebook configures pandas display options."""
        # Save original settings
        original_max_rows = pd.get_option("display.max_rows")

        # Run setup
        setup_notebook(pd_max_rows=50, pd_max_cols=10)

        # Check pandas options were set
        assert pd.get_option("display.max_rows") == 50
        assert pd.get_option("display.max_columns") == 10
        assert pd.get_option("display.width") == 1000

        # Restore original
        pd.set_option("display.max_rows", original_max_rows)

    @patch("kalshi_research.research.notebook_utils.plt")
    @patch("kalshi_research.research.notebook_utils.get_ipython")
    def test_setup_notebook_configures_matplotlib(
        self, mock_get_ipython: MagicMock, mock_plt: MagicMock
    ) -> None:
        """Test that setup_notebook configures matplotlib."""
        mock_ipython = MagicMock()
        mock_get_ipython.return_value = mock_ipython

        setup_notebook()

        # Check that IPython magic was called
        mock_ipython.run_line_magic.assert_any_call("matplotlib", "inline")
        assert mock_ipython.run_line_magic.call_count >= 1

    @patch("kalshi_research.research.notebook_utils.plt", None)
    def test_setup_notebook_without_matplotlib(self) -> None:
        """Test setup_notebook handles missing matplotlib gracefully."""
        # Should not raise even if matplotlib is not available
        setup_notebook()


class TestLoadMarkets:
    """Test load_markets function."""

    @pytest.mark.asyncio
    async def test_load_markets_returns_dataframe(self) -> None:
        """Test that load_markets returns a DataFrame."""
        mock_market = Market(
            ticker="TEST-TICKER",
            title="Test Market",
            subtitle="Test subtitle",
            event_ticker="TEST-EVENT",
            series_ticker="TEST-SERIES",
            status="active",
            yes_bid=48,
            yes_ask=52,
            yes_price=50,
            no_bid=48,
            no_ask=52,
            volume=1000,
            volume_24h=800,
            open_interest=500,
            liquidity=100,
            close_time=datetime(2025, 12, 31, tzinfo=UTC),
            open_time=datetime(2025, 1, 1, tzinfo=UTC),
            expiration_time=datetime(2026, 1, 1, tzinfo=UTC),
        )

        async def mock_get_all_markets(status: str) -> list[Market]:
            for m in [mock_market]:
                yield m

        with patch(
            "kalshi_research.research.notebook_utils.KalshiPublicClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get_all_markets = mock_get_all_markets
            mock_client_class.return_value = mock_client

            df = await load_markets(status="open", limit=10)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "ticker" in df.columns
        assert "title" in df.columns
        assert "yes_price" in df.columns
        assert df.iloc[0]["ticker"] == "TEST-TICKER"

    @pytest.mark.asyncio
    async def test_load_markets_respects_limit(self) -> None:
        """Test that load_markets respects the limit parameter."""
        mock_markets = [
            Market(
                ticker=f"TEST-{i}",
                title=f"Test {i}",
                subtitle="",
                event_ticker="TEST-EVENT",
                series_ticker="TEST-SERIES",
                status="active",
                yes_bid=48,
                yes_ask=52,
                yes_price=50,
                no_bid=48,
                no_ask=52,
                volume=1000,
                volume_24h=800,
                open_interest=500,
                liquidity=100,
                close_time=datetime(2025, 12, 31, tzinfo=UTC),
                open_time=datetime(2025, 1, 1, tzinfo=UTC),
                expiration_time=datetime(2026, 1, 1, tzinfo=UTC),
            )
            for i in range(100)
        ]

        async def mock_get_all_markets(status: str) -> list[Market]:
            for m in mock_markets:
                yield m

        with patch(
            "kalshi_research.research.notebook_utils.KalshiPublicClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get_all_markets = mock_get_all_markets
            mock_client_class.return_value = mock_client

            df = await load_markets(status="open", limit=5)

        assert len(df) == 5

    @pytest.mark.asyncio
    async def test_load_markets_calculates_spread(self) -> None:
        """Test that load_markets calculates spread correctly."""
        mock_market = Market(
            ticker="TEST-TICKER",
            title="Test Market",
            subtitle="",
            event_ticker="TEST-EVENT",
            series_ticker="TEST-SERIES",
            status="active",
            yes_bid=45,
            yes_ask=55,
            yes_price=50,
            no_bid=45,
            no_ask=55,
            volume=1000,
            volume_24h=800,
            open_interest=500,
            liquidity=100,
            close_time=datetime(2025, 12, 31, tzinfo=UTC),
            open_time=datetime(2025, 1, 1, tzinfo=UTC),
            expiration_time=datetime(2026, 1, 1, tzinfo=UTC),
        )

        async def mock_get_all_markets(status: str) -> list[Market]:
            for m in [mock_market]:
                yield m

        with patch(
            "kalshi_research.research.notebook_utils.KalshiPublicClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get_all_markets = mock_get_all_markets
            mock_client_class.return_value = mock_client

            df = await load_markets()

        assert df.iloc[0]["spread"] == 10  # 55 - 45


class TestLoadEvents:
    """Test load_events function."""

    @pytest.mark.asyncio
    async def test_load_events_returns_dataframe(self) -> None:
        """Test that load_events returns a DataFrame."""
        mock_event = Event(
            event_ticker="TEST-EVENT",
            series_ticker="TEST-SERIES",
            title="Test Event",
            category="test",
            mutually_exclusive=True,
        )

        async def mock_get_all_events() -> list[Event]:
            for e in [mock_event]:
                yield e

        with patch(
            "kalshi_research.research.notebook_utils.KalshiPublicClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get_all_events = mock_get_all_events
            mock_client_class.return_value = mock_client

            df = await load_events(limit=10)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "event_ticker" in df.columns
        assert "title" in df.columns
        assert df.iloc[0]["event_ticker"] == "TEST-EVENT"


class TestDisplayMarket:
    """Test display_market function."""

    @patch("kalshi_research.research.notebook_utils.display")
    def test_display_market_shows_html(self, mock_display: MagicMock) -> None:
        """Test that display_market renders HTML."""
        market = Market(
            ticker="TEST-TICKER",
            title="Test Market",
            subtitle="Test subtitle",
            event_ticker="TEST-EVENT",
            series_ticker="TEST-SERIES",
            status="active",
            yes_bid=48,
            yes_ask=52,
            yes_price=50,
            no_bid=48,
            no_ask=52,
            volume=1000,
            volume_24h=800,
            open_interest=500,
            liquidity=100,
            close_time=datetime(2025, 12, 31, tzinfo=UTC),
            open_time=datetime(2025, 1, 1, tzinfo=UTC),
            expiration_time=datetime(2026, 1, 1, tzinfo=UTC),
        )

        display_market(market)

        # Check that display was called with HTML
        mock_display.assert_called_once()
        call_args = mock_display.call_args[0][0]
        # HTML object has .data attribute
        assert hasattr(call_args, "data")
        assert "TEST-TICKER" in call_args.data


class TestDisplayEdge:
    """Test display_edge function."""

    @patch("kalshi_research.research.notebook_utils.display")
    def test_display_edge_shows_html(self, mock_display: MagicMock) -> None:
        """Test that display_edge renders HTML."""
        edge = Edge(
            ticker="TEST-TICKER",
            edge_type=EdgeType.THESIS,
            market_price=0.50,
            your_estimate=0.65,
            expected_value=10.0,
            confidence=0.75,
            description="Strong edge based on thesis",
        )

        display_edge(edge)

        # Check that display was called with HTML
        mock_display.assert_called_once()
        call_args = mock_display.call_args[0][0]
        assert hasattr(call_args, "data")
        assert "TEST-TICKER" in call_args.data
        assert "THESIS" in call_args.data

    @patch("kalshi_research.research.notebook_utils.display")
    def test_display_edge_colors_by_value(self, mock_display: MagicMock) -> None:
        """Test that display_edge uses correct colors for positive/negative EV."""
        # Positive EV edge
        edge_positive = Edge(
            ticker="TEST-TICKER",
            edge_type=EdgeType.THESIS,
            market_price=0.50,
            your_estimate=0.65,
            expected_value=10.0,
            confidence=0.75,
            description="Positive edge",
        )

        display_edge(edge_positive)
        html_data = mock_display.call_args[0][0].data
        assert "green" in html_data

        # Negative EV edge
        mock_display.reset_mock()
        edge_negative = Edge(
            ticker="TEST-TICKER",
            edge_type=EdgeType.THESIS,
            market_price=0.50,
            your_estimate=0.35,
            expected_value=-10.0,
            confidence=0.75,
            description="Negative edge",
        )

        display_edge(edge_negative)
        html_data = mock_display.call_args[0][0].data
        assert "red" in html_data


class TestDisplayMarketsTable:
    """Test display_markets_table function."""

    @patch("kalshi_research.research.notebook_utils.display")
    def test_display_markets_table_with_dataframe(self, mock_display: MagicMock) -> None:
        """Test displaying markets from DataFrame."""
        df = pd.DataFrame(
            [
                {
                    "ticker": "TEST-1",
                    "title": "Test Market 1",
                    "yes_price": "50c",
                    "spread": "4c",
                    "volume": "1000",
                    "status": "open",
                },
                {
                    "ticker": "TEST-2",
                    "title": "Test Market 2",
                    "yes_price": "60c",
                    "spread": "5c",
                    "volume": "2000",
                    "status": "open",
                },
            ]
        )

        display_markets_table(df)

        mock_display.assert_called_once()

    @patch("kalshi_research.research.notebook_utils.display")
    def test_display_markets_table_with_market_list(self, mock_display: MagicMock) -> None:
        """Test displaying markets from list of Market objects."""
        markets = [
            Market(
                ticker="TEST-1",
                title="Test Market 1",
                subtitle="",
                event_ticker="TEST-EVENT",
                series_ticker="TEST-SERIES",
                status="active",
                yes_bid=48,
                yes_ask=52,
                yes_price=50,
                no_bid=48,
                no_ask=52,
                volume=1000,
                volume_24h=800,
                open_interest=500,
                liquidity=100,
                close_time=datetime(2025, 12, 31, tzinfo=UTC),
                open_time=datetime(2025, 1, 1, tzinfo=UTC),
                expiration_time=datetime(2026, 1, 1, tzinfo=UTC),
            )
        ]

        display_markets_table(markets)

        mock_display.assert_called_once()


class TestRunAsync:
    """Test run_async helper function."""

    @pytest.mark.asyncio
    async def test_run_async_executes_coroutine(self) -> None:
        """Test that run_async executes async coroutines."""

        async def sample_coro() -> str:
            return "success"

        result = run_async(sample_coro())
        assert result == "success"
