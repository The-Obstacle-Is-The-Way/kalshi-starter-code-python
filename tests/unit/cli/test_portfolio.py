from __future__ import annotations

import base64
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import Response
from typer.testing import CliRunner

from kalshi_research.cli import app
from tests.unit.cli.fixtures import KALSHI_DEMO_BASE_URL, load_portfolio_balance_fixture

runner = CliRunner()


def test_portfolio_balance_requires_auth() -> None:
    with patch.dict(
        os.environ,
        {
            "KALSHI_KEY_ID": "",
            "KALSHI_PRIVATE_KEY_PATH": "",
            "KALSHI_PRIVATE_KEY_B64": "",
        },
        clear=False,
    ):
        result = runner.invoke(app, ["portfolio", "balance"])

    assert result.exit_code == 1
    assert "Balance requires authentication" in result.stdout


def test_portfolio_balance_invalid_private_key_b64_exits_cleanly() -> None:
    with patch.dict(
        os.environ,
        {
            "KALSHI_KEY_ID": "dummy",
            "KALSHI_PRIVATE_KEY_B64": "not base64",
        },
        clear=False,
    ):
        result = runner.invoke(app, ["portfolio", "balance"])

    assert result.exit_code == 1
    assert "Invalid base64 private key" in result.stdout


@respx.mock
def test_portfolio_balance_loads_dotenv() -> None:
    with runner.isolated_filesystem():
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        private_key_b64 = base64.b64encode(pem).decode("utf-8")

        Path(".env").write_text(
            "\n".join(
                [
                    "KALSHI_KEY_ID=test-key-id",
                    f"KALSHI_PRIVATE_KEY_B64={private_key_b64}",
                    "KALSHI_ENVIRONMENT=demo",
                    "",
                ]
            )
        )

        fixture = load_portfolio_balance_fixture()
        respx.get(f"{KALSHI_DEMO_BASE_URL}/portfolio/balance").mock(
            return_value=Response(200, json=fixture)
        )

        with patch.dict(os.environ, {}, clear=True):
            result = runner.invoke(app, ["portfolio", "balance"])

    assert result.exit_code == 0
    assert "Account Balance" in result.stdout


@patch("kalshi_research.cli.db.DatabaseManager")
def test_portfolio_link_success(mock_db_cls: MagicMock) -> None:
    mock_position = MagicMock()
    mock_position.ticker = "TEST-TICKER"
    mock_position.thesis_id = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_position

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    # Mock session.begin() - use MagicMock (not AsyncMock) that returns async context manager
    begin_cm = AsyncMock()
    begin_cm.__aenter__.return_value = None
    begin_cm.__aexit__.return_value = None
    mock_session.begin = MagicMock(return_value=begin_cm)

    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["portfolio", "link", "TEST-TICKER", "--thesis", "thesis-123"])

    assert result.exit_code == 0
    assert "linked" in result.stdout.lower()


@patch("kalshi_research.cli.db.DatabaseManager")
def test_portfolio_link_position_not_found(mock_db_cls: MagicMock) -> None:
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    # Mock session.begin() - use MagicMock (not AsyncMock) that returns async context manager
    begin_cm = AsyncMock()
    begin_cm.__aenter__.return_value = None
    begin_cm.__aexit__.return_value = None
    mock_session.begin = MagicMock(return_value=begin_cm)

    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["portfolio", "link", "NONEXISTENT", "--thesis", "thesis-123"])

    assert result.exit_code == 0
    assert "not found" in result.stdout.lower() or "no open position" in result.stdout.lower()


@patch("kalshi_research.cli.db.DatabaseManager")
def test_portfolio_suggest_links_with_matches(mock_db_cls: MagicMock) -> None:
    mock_position = MagicMock()
    mock_position.ticker = "SENATE-2024"
    mock_position.thesis_id = None

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_position]

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    thesis_data = {
        "theses": [
            {
                "id": "thesis-12345678",
                "title": "Senate Control",
                "market_tickers": ["SENATE-2024"],
                "status": "active",
            }
        ]
    }
    mock_file = mock_open(read_data=json.dumps(thesis_data))

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.open", mock_file),
    ):
        result = runner.invoke(app, ["portfolio", "suggest-links"])

    assert result.exit_code == 0
    assert "suggest" in result.stdout.lower() or "SENATE-2024" in result.stdout


@patch("kalshi_research.cli.db.DatabaseManager")
def test_portfolio_suggest_links_no_matches(mock_db_cls: MagicMock) -> None:
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    with patch("pathlib.Path.exists", return_value=False):
        result = runner.invoke(app, ["portfolio", "suggest-links"])

    assert result.exit_code == 0
    assert "no" in result.stdout.lower() or "not found" in result.stdout.lower()


def test_portfolio_positions_fresh_db_does_not_crash() -> None:
    with runner.isolated_filesystem():
        db_path = Path("fresh.db")
        result = runner.invoke(app, ["portfolio", "positions", "--db", str(db_path)])

    assert result.exit_code == 0
    assert "No open positions found" in result.stdout


@patch("kalshi_research.cli.db.DatabaseManager")
def test_portfolio_positions_shows_zero_mark_price(mock_db_cls: MagicMock) -> None:
    mock_position = MagicMock()
    mock_position.ticker = "TEST-TICKER"
    mock_position.side = "yes"
    mock_position.quantity = 1
    mock_position.avg_price_cents = 10
    mock_position.current_price_cents = 0
    mock_position.unrealized_pnl_cents = 0
    mock_position.closed_at = None

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_position]

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = False
    mock_db.create_tables = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    result = runner.invoke(app, ["portfolio", "positions"])

    assert result.exit_code == 0
    assert "0¢" in result.stdout


@patch("kalshi_research.cli.db.DatabaseManager")
def test_portfolio_positions_shows_unknown_unrealized_pnl(mock_db_cls: MagicMock) -> None:
    mock_position = MagicMock()
    mock_position.ticker = "TEST-TICKER"
    mock_position.side = "yes"
    mock_position.quantity = 1
    mock_position.avg_price_cents = 0  # Unknown cost basis
    mock_position.current_price_cents = None  # Mark price not synced
    mock_position.unrealized_pnl_cents = None  # Unknown P&L
    mock_position.closed_at = None

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_position]

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = False
    mock_db.create_tables = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    result = runner.invoke(app, ["portfolio", "positions"])

    assert result.exit_code == 0
    assert "Total Unrealized P&L (known only)" in result.stdout
    assert "unknown unrealized p&l" in result.stdout.lower()


@patch("kalshi_research.cli.db.DatabaseManager")
def test_portfolio_positions_filters_by_ticker_and_formats_positive_pnl(
    mock_db_cls: MagicMock,
) -> None:
    mock_position = MagicMock()
    mock_position.ticker = "TEST-TICKER"
    mock_position.side = "yes"
    mock_position.quantity = 1
    mock_position.avg_price_cents = 10
    mock_position.current_price_cents = 20
    mock_position.unrealized_pnl_cents = 100
    mock_position.closed_at = None

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_position]

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_session_factory = MagicMock(return_value=mock_session)

    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = False
    mock_db.create_tables = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    result = runner.invoke(app, ["portfolio", "positions", "--ticker", "TEST-TICKER"])

    assert result.exit_code == 0
    assert "TEST-TICKER" in result.stdout
    assert "+$1.00" in result.stdout


@patch("kalshi_research.cli.db.DatabaseManager")
def test_portfolio_pnl_with_ticker_prints_summary(mock_db_cls: MagicMock) -> None:
    from kalshi_research.portfolio.pnl import PnLSummary

    mock_empty = MagicMock()
    mock_empty.scalars.return_value.all.return_value = []

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[mock_empty, mock_empty, mock_empty])

    mock_session_factory = MagicMock(return_value=mock_session)

    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = False
    mock_db.create_tables = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    summary = PnLSummary(
        unrealized_pnl_cents=0,
        realized_pnl_cents=0,
        total_pnl_cents=0,
        total_trades=0,
        winning_trades=0,
        losing_trades=0,
        win_rate=0.0,
        avg_win_cents=0,
        avg_loss_cents=0,
        profit_factor=0.0,
    )

    mock_calc = MagicMock()
    mock_calc.calculate_summary_with_trades.return_value = summary

    with patch("kalshi_research.portfolio.PnLCalculator", return_value=mock_calc):
        result = runner.invoke(app, ["portfolio", "pnl", "--ticker", "TEST-TICKER"])

    assert result.exit_code == 0
    assert "P&L Summary" in result.stdout


@patch("kalshi_research.cli.db.DatabaseManager")
def test_portfolio_history_renders_table_and_filters_by_ticker(mock_db_cls: MagicMock) -> None:
    trade = MagicMock()
    trade.executed_at = datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC)
    trade.ticker = "TEST-TICKER"
    trade.side = "yes"
    trade.action = "buy"
    trade.quantity = 10
    trade.price_cents = 55
    trade.total_cost_cents = 550

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [trade]

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_session_factory = MagicMock(return_value=mock_session)

    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = False
    mock_db.create_tables = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    result = runner.invoke(
        app,
        ["portfolio", "history", "--ticker", "TEST-TICKER", "--limit", "1"],
    )

    assert result.exit_code == 0
    assert "Trade History" in result.stdout
    assert "TEST-TICKER" in result.stdout


@patch("kalshi_research.cli.db.DatabaseManager")
def test_portfolio_suggest_links_positions_empty_prints_tip(mock_db_cls: MagicMock) -> None:
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_session_factory = MagicMock(return_value=mock_session)

    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    thesis_data = {
        "theses": [{"id": "thesis-12345678", "title": "Senate", "market_tickers": ["SENATE-2024"]}]
    }
    mock_file = mock_open(read_data=json.dumps(thesis_data))

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.open", mock_file),
    ):
        result = runner.invoke(app, ["portfolio", "suggest-links"])

    assert result.exit_code == 0
    assert "No unlinked positions found" in result.stdout
    assert "Tip: run" in result.stdout


@patch("kalshi_research.cli.db.DatabaseManager")
def test_portfolio_suggest_links_no_matching_pairs_prints_message(mock_db_cls: MagicMock) -> None:
    mock_position = MagicMock()
    mock_position.ticker = "OTHER-TICKER"
    mock_position.thesis_id = None

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_position]

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_session_factory = MagicMock(return_value=mock_session)

    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    thesis_data = {
        "theses": [{"id": "thesis-12345678", "title": "Senate", "market_tickers": ["SENATE-2024"]}]
    }
    mock_file = mock_open(read_data=json.dumps(thesis_data))

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.open", mock_file),
    ):
        result = runner.invoke(app, ["portfolio", "suggest-links"])

    assert result.exit_code == 0
    assert "No matching thesis-position pairs found" in result.stdout
