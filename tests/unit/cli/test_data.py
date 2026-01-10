from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from kalshi_research.api.models.trade import Trade
from kalshi_research.cli import app

runner = CliRunner()


@patch("kalshi_research.cli.db.DatabaseManager")
def test_data_init(mock_db_cls: MagicMock) -> None:
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = False
    mock_db.create_tables = AsyncMock()
    mock_db_cls.return_value = mock_db

    result = runner.invoke(app, ["data", "init"])

    assert result.exit_code == 0
    assert "Database initialized" in result.stdout
    mock_db.create_tables.assert_called_once()


@patch("kalshi_research.data.DataFetcher")
@patch("kalshi_research.cli.db.DatabaseManager")
def test_data_sync_markets(mock_db_cls: MagicMock, mock_fetcher_cls: MagicMock) -> None:
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    mock_db.create_tables = AsyncMock()
    mock_db_cls.return_value = mock_db

    mock_fetcher = AsyncMock()
    mock_fetcher.__aenter__.return_value = mock_fetcher
    mock_fetcher.__aexit__.return_value = None
    mock_fetcher.sync_events.return_value = 5
    mock_fetcher.sync_markets.return_value = 10
    mock_fetcher_cls.return_value = mock_fetcher

    result = runner.invoke(app, ["data", "sync-markets"])

    assert result.exit_code == 0
    assert "5 events" in result.stdout
    assert "10 markets" in result.stdout


@patch("kalshi_research.data.DataFetcher")
@patch("kalshi_research.cli.db.DatabaseManager")
def test_data_sync_settlements(mock_db_cls: MagicMock, mock_fetcher_cls: MagicMock) -> None:
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    mock_db.create_tables = AsyncMock()
    mock_db_cls.return_value = mock_db

    mock_fetcher = AsyncMock()
    mock_fetcher.__aenter__.return_value = mock_fetcher
    mock_fetcher.__aexit__.return_value = None
    mock_fetcher.sync_settlements.return_value = 123
    mock_fetcher_cls.return_value = mock_fetcher

    result = runner.invoke(app, ["data", "sync-settlements"])

    assert result.exit_code == 0
    assert "123 settlements" in result.stdout
    mock_fetcher.sync_settlements.assert_called_once_with(max_pages=None)


@patch("kalshi_research.data.DataFetcher")
@patch("kalshi_research.cli.db.DatabaseManager")
def test_data_snapshot(mock_db_cls: MagicMock, mock_fetcher_cls: MagicMock) -> None:
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    mock_db.create_tables = AsyncMock()
    mock_db_cls.return_value = mock_db

    mock_fetcher = AsyncMock()
    mock_fetcher.__aenter__.return_value = mock_fetcher
    mock_fetcher.__aexit__.return_value = None
    mock_fetcher.take_snapshot.return_value = 100
    mock_fetcher_cls.return_value = mock_fetcher

    result = runner.invoke(app, ["data", "snapshot"])

    assert result.exit_code == 0
    assert "Took 100 price snapshots" in result.stdout


@patch("kalshi_research.data.export.export_to_parquet")
def test_data_export(mock_export: MagicMock) -> None:
    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["data", "export", "--format", "parquet"])

    assert result.exit_code == 0
    assert "Exported to" in result.stdout
    mock_export.assert_called_once()


@patch("kalshi_research.data.DatabaseManager")
@patch("kalshi_research.data.repositories.EventRepository")
@patch("kalshi_research.data.repositories.MarketRepository")
@patch("kalshi_research.data.repositories.PriceRepository")
def test_data_stats(
    mock_price_repo_cls: MagicMock,
    mock_market_repo_cls: MagicMock,
    mock_event_repo_cls: MagicMock,
    mock_db_cls: MagicMock,
) -> None:
    with patch("pathlib.Path.exists", return_value=True):
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session_cm
        mock_session_cm.__aexit__.return_value = False

        mock_db = MagicMock()
        mock_db.session_factory = MagicMock(return_value=mock_session_cm)

        mock_db_cm = AsyncMock()
        mock_db_cm.__aenter__.return_value = mock_db
        mock_db_cm.__aexit__.return_value = False
        mock_db_cls.return_value = mock_db_cm

        mock_event_repo = MagicMock()
        mock_event_repo.get_all = AsyncMock(return_value=[1, 2, 3])
        mock_event_repo_cls.return_value = mock_event_repo

        mock_market_repo = MagicMock()
        mock_market_repo.get_all = AsyncMock(return_value=[1, 2])
        mock_market_repo.count_by_status = AsyncMock(return_value={"active": 2})
        mock_market_repo.get_active = AsyncMock(return_value=[MagicMock(ticker="TEST")])
        mock_market_repo_cls.return_value = mock_market_repo

        mock_price_repo = MagicMock()
        mock_price_repo.count_for_market = AsyncMock(return_value=10)
        mock_price_repo_cls.return_value = mock_price_repo

        result = runner.invoke(app, ["data", "stats"])

    assert result.exit_code == 0
    assert "Total Events" in result.stdout
    assert "3" in result.stdout


@patch("kalshi_research.api.KalshiPublicClient")
def test_data_sync_trades_exports_csv(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get_trades = AsyncMock(
        return_value=[
            Trade(
                trade_id="trade-1",
                ticker="TEST-TICKER",
                created_time=datetime.now(UTC),
                yes_price=51,
                no_price=49,
                count=10,
                taker_side="yes",
            )
        ]
    )
    mock_client_cls.return_value = mock_client

    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            [
                "data",
                "sync-trades",
                "--ticker",
                "TEST-TICKER",
                "--output",
                "trades.csv",
            ],
        )

        assert result.exit_code == 0
        assert "Exported 1 trades" in result.stdout
        csv_text = Path("trades.csv").read_text(encoding="utf-8")
        assert "trade_id,ticker,created_time,yes_price,no_price,count,taker_side" in csv_text
        assert "trade-1,TEST-TICKER" in csv_text


@patch("alembic.command.upgrade")
def test_data_migrate_dry_run_calls_alembic_upgrade(
    mock_upgrade: MagicMock, tmp_path: Path
) -> None:
    db_path = tmp_path / "kalshi.db"

    result = runner.invoke(app, ["data", "migrate", "--db", str(db_path), "--dry-run"])

    assert result.exit_code == 0
    mock_upgrade.assert_called_once()
    _, kwargs = mock_upgrade.call_args
    assert kwargs["sql"] is True


@patch("alembic.command.upgrade")
def test_data_migrate_apply_calls_alembic_upgrade(mock_upgrade: MagicMock, tmp_path: Path) -> None:
    db_path = tmp_path / "kalshi.db"

    result = runner.invoke(app, ["data", "migrate", "--db", str(db_path), "--apply"])

    assert result.exit_code == 0
    mock_upgrade.assert_called_once()
    _, kwargs = mock_upgrade.call_args
    assert kwargs == {}
