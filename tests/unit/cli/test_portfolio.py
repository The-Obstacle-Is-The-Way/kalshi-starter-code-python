from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

from typer.testing import CliRunner

from kalshi_research.cli import app

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


@patch("kalshi_research.api.KalshiClient")
def test_portfolio_balance_loads_dotenv(mock_client_cls: MagicMock) -> None:
    from kalshi_research.api.models.portfolio import PortfolioBalance

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get_balance = AsyncMock(
        return_value=PortfolioBalance(balance=123, portfolio_value=456)
    )
    mock_client_cls.return_value = mock_client

    with runner.isolated_filesystem():
        Path(".env").write_text(
            "\n".join(
                [
                    "KALSHI_KEY_ID=test-key-id",
                    "KALSHI_PRIVATE_KEY_B64=test-private-key-b64",
                    "KALSHI_ENVIRONMENT=demo",
                    "",
                ]
            )
        )

        with patch.dict(os.environ, {}, clear=True):
            result = runner.invoke(app, ["portfolio", "balance"])

    assert result.exit_code == 0
    assert "Account Balance" in result.stdout


@patch("kalshi_research.data.DatabaseManager")
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


@patch("kalshi_research.data.DatabaseManager")
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


@patch("kalshi_research.data.DatabaseManager")
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


@patch("kalshi_research.data.DatabaseManager")
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


@patch("kalshi_research.data.DatabaseManager")
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
    mock_db.session_factory = mock_session_factory
    mock_db.close = AsyncMock()
    mock_db_cls.return_value = mock_db

    result = runner.invoke(app, ["portfolio", "positions"])

    assert result.exit_code == 0
    assert "0¢" in result.stdout


@patch("kalshi_research.data.DatabaseManager")
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
    mock_db.session_factory = mock_session_factory
    mock_db.close = AsyncMock()
    mock_db_cls.return_value = mock_db

    result = runner.invoke(app, ["portfolio", "positions"])

    assert result.exit_code == 0
    assert "Total Unrealized P&L (known only)" in result.stdout
    assert "unknown unrealized p&l" in result.stdout.lower()
