from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from kalshi_research.cli import app

runner = CliRunner()

OPEN_DB_SESSION = "kalshi_research.cli.db.open_db_session"
HAS_FTS5_SUPPORT = "kalshi_research.data.search_utils.has_fts5_support"
SEARCH_MARKETS = "kalshi_research.data.repositories.search.SearchRepository.search_markets"


def test_market_search_rejects_invalid_format() -> None:
    result = runner.invoke(app, ["market", "search", "test", "--format", "nope"])
    assert result.exit_code == 2
    assert "format must be 'table' or 'json'" in result.output


def test_market_search_missing_db_exits_1() -> None:
    result = runner.invoke(app, ["market", "search", "test", "--db", "missing.db"])
    assert result.exit_code == 1
    assert "Database file not found" in result.stdout


def test_market_search_json_output_handles_none_timestamps() -> None:
    with runner.isolated_filesystem():
        db_path = Path("db.sqlite")
        db_path.touch()

        @asynccontextmanager
        async def fake_open_db_session(_path: Path):
            yield AsyncMock()

        now = datetime.now(UTC)
        fake_results = [
            SimpleNamespace(
                ticker="TICK",
                title="Test market",
                subtitle=None,
                event_ticker="EVT",
                event_category="Politics",
                status="open",
                midpoint=0.5,
                spread=2,
                volume_24h=123,
                close_time=None,
                expiration_time=None,
            ),
            SimpleNamespace(
                ticker="TICK2",
                title="Test market 2",
                subtitle="Sub",
                event_ticker="EVT2",
                event_category=None,
                status="open",
                midpoint=0.51,
                spread=None,
                volume_24h=None,
                close_time=now,
                expiration_time=now,
            ),
        ]

        with (
            patch(OPEN_DB_SESSION, fake_open_db_session),
            patch(HAS_FTS5_SUPPORT, AsyncMock(return_value=True)),
            patch(SEARCH_MARKETS, AsyncMock(return_value=fake_results)),
        ):
            result = runner.invoke(
                app,
                [
                    "market",
                    "search",
                    "test",
                    "--db",
                    str(db_path),
                    "--format",
                    "json",
                ],
            )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload[0]["ticker"] == "TICK"
    assert payload[0]["close_time"] is None
    assert payload[0]["expiration_time"] is None
    assert payload[1]["ticker"] == "TICK2"
    assert payload[1]["close_time"] is not None
    assert payload[1]["expiration_time"] is not None


def test_market_search_table_output_renders_results() -> None:
    with runner.isolated_filesystem():
        db_path = Path("db.sqlite")
        db_path.touch()

        @asynccontextmanager
        async def fake_open_db_session(_path: Path):
            yield AsyncMock()

        fake_results = [
            SimpleNamespace(
                ticker="TICK",
                title="Test market",
                subtitle=None,
                event_ticker="EVT",
                event_category="Politics",
                status="open",
                midpoint=0.5,
                spread=2,
                volume_24h=123,
                close_time=None,
                expiration_time=None,
            )
        ]

        with (
            patch(OPEN_DB_SESSION, fake_open_db_session),
            patch(HAS_FTS5_SUPPORT, AsyncMock(return_value=True)),
            patch(SEARCH_MARKETS, AsyncMock(return_value=fake_results)),
        ):
            result = runner.invoke(
                app,
                [
                    "market",
                    "search",
                    "test",
                    "--db",
                    str(db_path),
                    "--format",
                    "table",
                ],
            )

    assert result.exit_code == 0
    assert "TICK" in result.stdout
    assert "Test market" in result.stdout
