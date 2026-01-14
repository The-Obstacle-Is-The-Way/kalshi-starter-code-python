from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import respx
from httpx import Response
from typer.testing import CliRunner

from kalshi_research.api.models.portfolio import (
    FillPage,
    PortfolioBalance,
    PortfolioPosition,
    SettlementPage,
)
from kalshi_research.cli import app
from kalshi_research.data import DatabaseManager
from kalshi_research.data.models import Event, Market, PriceSnapshot

pytestmark = [pytest.mark.integration]


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _event_dict(event_ticker: str = "EVT1") -> dict[str, Any]:
    return {
        "event_ticker": event_ticker,
        "series_ticker": "SERIES1",
        "title": "Event 1",
        "category": "Test",
    }


def _market_dict(
    ticker: str,
    *,
    event_ticker: str = "EVT1",
    yes_bid: int = 49,
    yes_ask: int = 51,
    status: str = "active",
    volume_24h: int = 10_000,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "ticker": ticker,
        "event_ticker": event_ticker,
        "series_ticker": "SERIES1",
        "title": f"Market {ticker}",
        "subtitle": "",
        "status": status,
        "result": "",
        "yes_bid": yes_bid,
        "yes_ask": yes_ask,
        "no_bid": 100 - yes_ask,
        "no_ask": 100 - yes_bid,
        "last_price": (yes_bid + yes_ask) // 2,
        "volume": 1_000,
        "volume_24h": volume_24h,
        "open_interest": 100,
        "liquidity": 1_000,
        "open_time": "2024-01-01T00:00:00Z",
        "close_time": (now + timedelta(days=30)).isoformat().replace("+00:00", "Z"),
        "expiration_time": (now + timedelta(days=31)).isoformat().replace("+00:00", "Z"),
    }


def _mock_events_and_markets(
    *,
    events: list[dict[str, Any]] | None = None,
    markets: list[dict[str, Any]] | None = None,
) -> None:
    respx.get("https://api.elections.kalshi.com/trade-api/v2/events").mock(
        return_value=Response(
            200,
            json={"events": events or [_event_dict()], "cursor": None, "milestones": []},
        )
    )
    respx.get("https://api.elections.kalshi.com/trade-api/v2/markets").mock(
        return_value=Response(
            200, json={"markets": markets or [_market_dict("MKT1")], "cursor": None}
        )
    )


def test_version_command(runner: CliRunner) -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "kalshi-research v" in result.stdout


def test_data_init_and_stats(runner: CliRunner) -> None:
    with runner.isolated_filesystem():
        db_path = Path("data/test.db")

        missing = runner.invoke(app, ["data", "stats", "--db", str(db_path)])
        assert missing.exit_code == 1
        assert "Database not found" in missing.stdout

        init = runner.invoke(app, ["data", "init", "--db", str(db_path)])
        assert init.exit_code == 0
        assert db_path.exists()

        stats = runner.invoke(app, ["data", "stats", "--db", str(db_path)])
        assert stats.exit_code == 0
        assert "Database Statistics" in stats.stdout


@respx.mock
def test_data_sync_snapshot_and_collect_once(runner: CliRunner) -> None:
    with runner.isolated_filesystem():
        db_path = Path("data/test.db")

        init = runner.invoke(app, ["data", "init", "--db", str(db_path)])
        assert init.exit_code == 0

        _mock_events_and_markets(markets=[_market_dict("MKT1")])

        sync = runner.invoke(app, ["data", "sync-markets", "--db", str(db_path)])
        assert sync.exit_code == 0
        assert "Synced 1 events and 1 markets" in sync.stdout

        snapshot = runner.invoke(
            app,
            [
                "data",
                "snapshot",
                "--db",
                str(db_path),
                "--status",
                "open",
                "--max-pages",
                "1",
            ],
        )
        assert snapshot.exit_code == 0
        assert "Took 1 price snapshots" in snapshot.stdout

        collect = runner.invoke(
            app, ["data", "collect", "--db", str(db_path), "--once", "--max-pages", "1"]
        )
        assert collect.exit_code == 0
        assert "Full sync complete" in collect.stdout


def test_data_collect_daemon_schedules_tasks_and_exits_cleanly(runner: CliRunner) -> None:
    class _FakeFetcher:
        last: _FakeFetcher | None = None

        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs
            _FakeFetcher.last = self
            self.full_sync_calls: list[int | None] = []
            self.sync_markets_calls: list[tuple[str | None, int | None]] = []
            self.take_snapshot_calls: list[tuple[str | None, int | None]] = []

        async def __aenter__(self) -> _FakeFetcher:
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: object,
        ) -> None:
            return None

        async def full_sync(
            self,
            *,
            max_pages: int | None = None,
            include_multivariate: bool = False,
        ) -> dict[str, int]:
            del include_multivariate
            self.full_sync_calls.append(max_pages)
            return {"events": 0, "markets": 0, "snapshots": 0}

        async def sync_markets(
            self,
            status: str | None = None,
            *,
            max_pages: int | None = None,
            mve_filter: object | None = None,
        ) -> int:
            del mve_filter
            self.sync_markets_calls.append((status, max_pages))
            return 0

        async def take_snapshot(
            self, status: str | None = "open", *, max_pages: int | None = None
        ) -> int:
            self.take_snapshot_calls.append((status, max_pages))
            return 0

    class _FakeScheduler:
        last: _FakeScheduler | None = None

        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs
            _FakeScheduler.last = self
            self.scheduled: list[tuple[str, object, int, bool]] = []

        async def schedule_interval(
            self,
            name: str,
            task: object,
            *,
            interval_seconds: int,
            run_immediately: bool = True,
        ) -> None:
            self.scheduled.append((name, task, interval_seconds, run_immediately))

        async def __aenter__(self) -> _FakeScheduler:
            for _, task, _, _ in self.scheduled:
                await task()
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: object,
        ) -> None:
            return None

    async def _cancel_sleep(seconds: float) -> None:
        if seconds <= 0:
            return None
        raise asyncio.CancelledError

    with runner.isolated_filesystem():
        db_path = Path("data/test.db")
        init = runner.invoke(app, ["data", "init", "--db", str(db_path)])
        assert init.exit_code == 0

        with (
            patch("kalshi_research.data.DataFetcher", _FakeFetcher),
            patch("kalshi_research.data.DataScheduler", _FakeScheduler),
            patch("kalshi_research.cli.data.asyncio.sleep", new=_cancel_sleep),
        ):
            result = runner.invoke(
                app,
                [
                    "data",
                    "collect",
                    "--db",
                    str(db_path),
                    "--interval",
                    "1",
                    "--max-pages",
                    "1",
                ],
            )

        assert result.exit_code == 0

        assert _FakeScheduler.last is not None
        assert [run_immediately for *_, run_immediately in _FakeScheduler.last.scheduled] == [
            False,
            False,
        ]

        assert _FakeFetcher.last is not None
        assert _FakeFetcher.last.full_sync_calls == [1]
        assert _FakeFetcher.last.sync_markets_calls == [("open", 1)]
        assert _FakeFetcher.last.take_snapshot_calls == [("open", 1)]


def test_data_export_errors_and_unknown_format(runner: CliRunner) -> None:
    with runner.isolated_filesystem():
        db_path = Path("data/test.db")
        output_dir = Path("exports")

        missing = runner.invoke(
            app,
            [
                "data",
                "export",
                "--db",
                str(db_path),
                "--output",
                str(output_dir),
                "--format",
                "csv",
            ],
        )
        assert missing.exit_code == 1
        assert "Database not found" in missing.stdout

        init = runner.invoke(app, ["data", "init", "--db", str(db_path)])
        assert init.exit_code == 0

        invalid = runner.invoke(
            app,
            [
                "data",
                "export",
                "--db",
                str(db_path),
                "--output",
                str(output_dir),
                "--format",
                "nope",
            ],
        )
        assert invalid.exit_code == 1
        assert "Unknown format" in invalid.stdout


@respx.mock
def test_market_commands(runner: CliRunner) -> None:
    with runner.isolated_filesystem():
        ticker = "MKT1"
        respx.get(f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}").mock(
            return_value=Response(200, json={"market": _market_dict(ticker)})
        )
        respx.get(f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}/orderbook").mock(
            return_value=Response(200, json={"orderbook": {"yes": [[49, 10]], "no": [[51, 10]]}})
        )
        _mock_events_and_markets(markets=[_market_dict(ticker)])

        get_cmd = runner.invoke(app, ["market", "get", ticker])
        assert get_cmd.exit_code == 0
        assert ticker in get_cmd.stdout

        ob_cmd = runner.invoke(app, ["market", "orderbook", ticker, "--depth", "1"])
        assert ob_cmd.exit_code == 0
        assert "Orderbook" in ob_cmd.stdout

        list_cmd = runner.invoke(app, ["market", "list", "--status", "open", "--limit", "1"])
        assert list_cmd.exit_code == 0
        assert "Markets (status=open)" in list_cmd.stdout


@respx.mock
def test_scan_commands(runner: CliRunner) -> None:
    with runner.isolated_filesystem():
        markets = [
            _market_dict("MKT1", yes_bid=49, yes_ask=51, volume_24h=20_000),
            _market_dict("MKT2", yes_bid=10, yes_ask=20, volume_24h=100),
        ]
        _mock_events_and_markets(markets=markets)

        opp = runner.invoke(app, ["scan", "opportunities", "--top", "5", "--max-pages", "1"])
        assert opp.exit_code == 0
        assert "Scan Results" in opp.stdout

        bad_filter = runner.invoke(app, ["scan", "opportunities", "--filter", "nope"])
        assert bad_filter.exit_code == 1
        assert "Unknown filter" in bad_filter.stdout

        arb = runner.invoke(app, ["scan", "arbitrage", "--db", "data/missing.db"])
        assert arb.exit_code == 0


@respx.mock
def test_scan_movers_errors_and_success(runner: CliRunner) -> None:
    with runner.isolated_filesystem():
        db_path = Path("data/test.db")
        init = runner.invoke(app, ["data", "init", "--db", str(db_path)])
        assert init.exit_code == 0

        missing_db = runner.invoke(app, ["scan", "movers", "--db", "data/missing.db"])
        assert missing_db.exit_code == 1
        assert "Database not found" in missing_db.stdout

        invalid_period = runner.invoke(
            app, ["scan", "movers", "--db", str(db_path), "--period", "nope"]
        )
        assert invalid_period.exit_code == 1
        assert "Invalid period" in invalid_period.stdout

        _mock_events_and_markets(markets=[_market_dict("MKT1")])

        async def _seed() -> None:
            async with DatabaseManager(db_path) as db:
                await db.create_tables()
                now = datetime.now(UTC)
                async with db.session_factory() as session:
                    session.add(Event(ticker="EVT1", series_ticker="S1", title="Event 1"))
                    session.add(
                        Market(
                            ticker="MKT1",
                            event_ticker="EVT1",
                            title="Market 1",
                            status="active",
                            open_time=now - timedelta(days=1),
                            close_time=now + timedelta(days=1),
                            expiration_time=now + timedelta(days=2),
                        )
                    )
                    session.add(
                        PriceSnapshot(
                            ticker="MKT1",
                            snapshot_time=now - timedelta(minutes=30),
                            yes_bid=40,
                            yes_ask=42,
                            no_bid=58,
                            no_ask=60,
                            last_price=41,
                            volume=100,
                            volume_24h=100,
                            open_interest=50,
                        )
                    )
                    session.add(
                        PriceSnapshot(
                            ticker="MKT1",
                            snapshot_time=now,
                            yes_bid=60,
                            yes_ask=62,
                            no_bid=38,
                            no_ask=40,
                            last_price=61,
                            volume=200,
                            volume_24h=200,
                            open_interest=100,
                        )
                    )
                    await session.commit()

        asyncio.run(_seed())

        movers = runner.invoke(
            app, ["scan", "movers", "--db", str(db_path), "--period", "1h", "--top", "5"]
        )
        assert movers.exit_code == 0
        assert "Biggest Movers" in movers.stdout


def test_alerts_commands(runner: CliRunner) -> None:
    with runner.isolated_filesystem():
        no_alerts = runner.invoke(app, ["alerts", "list"])
        assert no_alerts.exit_code == 0
        assert "No active alerts" in no_alerts.stdout

        missing_threshold = runner.invoke(app, ["alerts", "add", "price", "MKT1"])
        assert missing_threshold.exit_code == 1
        assert "Must specify either --above or --below" in missing_threshold.stdout

        bad_type = runner.invoke(app, ["alerts", "add", "nope", "MKT1", "--above", "0.6"])
        assert bad_type.exit_code == 1
        assert "Unknown alert type" in bad_type.stdout

        added = runner.invoke(app, ["alerts", "add", "price", "MKT1", "--above", "0.6"])
        assert added.exit_code == 0
        assert "Alert added" in added.stdout

        data = json.loads(Path("data/alerts.json").read_text())
        alert_id = data["conditions"][0]["id"][:8]

        listed = runner.invoke(app, ["alerts", "list"])
        assert listed.exit_code == 0
        assert "Active Alerts" in listed.stdout

        removed = runner.invoke(app, ["alerts", "remove", alert_id])
        assert removed.exit_code == 0
        assert "Alert removed" in removed.stdout

        monitor = runner.invoke(app, ["alerts", "monitor", "--interval", "1"])
        assert monitor.exit_code == 0
        assert "No alerts configured" in monitor.stdout


def test_research_thesis_commands(runner: CliRunner) -> None:
    with runner.isolated_filesystem():
        created = runner.invoke(
            app,
            [
                "research",
                "thesis",
                "create",
                "Test Thesis",
                "--markets",
                "MKT1,MKT2",
                "--your-prob",
                "0.6",
                "--market-prob",
                "0.5",
                "--confidence",
                "0.7",
            ],
        )
        assert created.exit_code == 0
        assert "Thesis created" in created.stdout

        data = json.loads(Path("data/theses.json").read_text())
        thesis_id = data["theses"][0]["id"][:8]

        listed = runner.invoke(app, ["research", "thesis", "list"])
        assert listed.exit_code == 0
        assert "Research Theses" in listed.stdout

        shown = runner.invoke(app, ["research", "thesis", "show", thesis_id])
        assert shown.exit_code == 0
        assert "Test Thesis" in shown.stdout

        resolved = runner.invoke(
            app,
            ["research", "thesis", "resolve", thesis_id, "--outcome", "yes"],
        )
        assert resolved.exit_code == 0
        assert "Thesis resolved" in resolved.stdout


def test_analysis_commands_error_paths_and_smoke(runner: CliRunner) -> None:
    with runner.isolated_filesystem():
        db_path = Path("data/test.db")

        missing = runner.invoke(app, ["analysis", "calibration", "--db", str(db_path)])
        assert missing.exit_code == 1
        assert "Database not found" in missing.stdout

        init = runner.invoke(app, ["data", "init", "--db", str(db_path)])
        assert init.exit_code == 0

        cal = runner.invoke(app, ["analysis", "calibration", "--db", str(db_path), "--days", "7"])
        assert cal.exit_code == 0
        assert "No settled markets" in cal.stdout

        metrics = runner.invoke(app, ["analysis", "metrics", "MKT1", "--db", str(db_path)])
        assert metrics.exit_code == 0
        assert "No data found" in metrics.stdout

        corr = runner.invoke(app, ["analysis", "correlation", "--db", str(db_path)])
        assert corr.exit_code == 1
        assert "Must specify --event or --tickers" in corr.stdout


def test_analysis_correlation_success(runner: CliRunner) -> None:
    with runner.isolated_filesystem():
        db_path = Path("data/test.db")
        init = runner.invoke(app, ["data", "init", "--db", str(db_path)])
        assert init.exit_code == 0

        async def _seed() -> None:
            async with DatabaseManager(db_path) as db:
                await db.create_tables()
                now = datetime.now(UTC)
                async with db.session_factory() as session:
                    session.add(Event(ticker="EVT1", series_ticker="S1", title="Event 1"))
                    session.add(
                        Market(
                            ticker="MKT1",
                            event_ticker="EVT1",
                            title="Market 1",
                            status="active",
                            open_time=now - timedelta(days=1),
                            close_time=now + timedelta(days=1),
                            expiration_time=now + timedelta(days=2),
                        )
                    )
                    session.add(
                        Market(
                            ticker="MKT2",
                            event_ticker="EVT1",
                            title="Market 2",
                            status="active",
                            open_time=now - timedelta(days=1),
                            close_time=now + timedelta(days=1),
                            expiration_time=now + timedelta(days=2),
                        )
                    )

                    for i in range(30):
                        t = now - timedelta(hours=30 - i)
                        yes_bid = 40 + i
                        yes_ask = 42 + i
                        session.add(
                            PriceSnapshot(
                                ticker="MKT1",
                                snapshot_time=t,
                                yes_bid=yes_bid,
                                yes_ask=yes_ask,
                                no_bid=100 - yes_ask,
                                no_ask=100 - yes_bid,
                                last_price=yes_bid,
                                volume=100,
                                volume_24h=100,
                                open_interest=50,
                            )
                        )
                        session.add(
                            PriceSnapshot(
                                ticker="MKT2",
                                snapshot_time=t,
                                yes_bid=yes_bid,
                                yes_ask=yes_ask,
                                no_bid=100 - yes_ask,
                                no_ask=100 - yes_bid,
                                last_price=yes_bid,
                                volume=100,
                                volume_24h=100,
                                open_interest=50,
                            )
                        )
                    await session.commit()

        asyncio.run(_seed())

        corr = runner.invoke(
            app,
            ["analysis", "correlation", "--db", str(db_path), "--event", "EVT1", "--min", "0.9"],
        )
        assert corr.exit_code == 0
        assert "Market Correlations" in corr.stdout
        assert "Found" in corr.stdout


def test_portfolio_commands_smoke(runner: CliRunner) -> None:
    class _FakeKalshiClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> _FakeKalshiClient:
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: object,
        ) -> None:
            return None

        async def get_positions(self) -> list[PortfolioPosition]:
            return []

        async def get_fills(self, **_: object) -> FillPage:
            return FillPage(fills=[], cursor=None)

        async def get_settlements(self, **_: object) -> SettlementPage:
            return SettlementPage(settlements=[], cursor=None)

        async def get_balance(self) -> PortfolioBalance:
            return PortfolioBalance(balance=0, portfolio_value=0)

    with runner.isolated_filesystem():
        db_path = Path("data/test.db")
        init = runner.invoke(app, ["data", "init", "--db", str(db_path)])
        assert init.exit_code == 0

        env = {
            "KALSHI_KEY_ID": "test",
            "KALSHI_PRIVATE_KEY_PATH": "dummy.pem",
            "KALSHI_ENVIRONMENT": "demo",
        }
        with patch("kalshi_research.api.KalshiClient", _FakeKalshiClient):
            sync = runner.invoke(app, ["portfolio", "sync", "--db", str(db_path)], env=env)
            assert sync.exit_code == 0
            assert "Synced" in sync.stdout

        positions = runner.invoke(app, ["portfolio", "positions", "--db", str(db_path)])
        assert positions.exit_code == 0
        assert "No open positions found" in positions.stdout

        pnl = runner.invoke(app, ["portfolio", "pnl", "--db", str(db_path)])
        assert pnl.exit_code == 0
        assert "P&L Summary" in pnl.stdout

        history = runner.invoke(app, ["portfolio", "history", "--db", str(db_path)])
        assert history.exit_code == 0
        assert "No trades found" in history.stdout

        with patch("kalshi_research.api.KalshiClient", _FakeKalshiClient):
            balance = runner.invoke(app, ["portfolio", "balance"], env=env)
            assert balance.exit_code == 0
            assert "Account Balance" in balance.stdout

        link = runner.invoke(
            app, ["portfolio", "link", "MKT1", "--thesis", "123", "--db", str(db_path)]
        )
        assert link.exit_code == 2
        assert "No open position found" in link.stdout

        suggest = runner.invoke(app, ["portfolio", "suggest-links", "--db", str(db_path)])
        assert suggest.exit_code == 0
        assert "No theses found" in suggest.stdout


@patch("duckdb.connect")
def test_data_export_success_smoke(mock_connect: MagicMock, runner: CliRunner) -> None:
    mock_connect.return_value = MagicMock()

    with runner.isolated_filesystem():
        db_path = Path("data/test.db")
        out_dir = Path("exports")

        init = runner.invoke(app, ["data", "init", "--db", str(db_path)])
        assert init.exit_code == 0

        exported = runner.invoke(
            app,
            ["data", "export", "--db", str(db_path), "--output", str(out_dir), "--format", "csv"],
        )
        assert exported.exit_code == 0
        assert "Exported to" in exported.stdout
