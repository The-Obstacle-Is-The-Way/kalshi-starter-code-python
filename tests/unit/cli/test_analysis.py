from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from kalshi_research.cli import app

runner = CliRunner()


@patch("kalshi_research.analysis.CalibrationAnalyzer")
@patch("kalshi_research.data.DatabaseManager")
def test_analysis_calibration(mock_db_cls: MagicMock, mock_analyzer_cls: MagicMock) -> None:
    from datetime import UTC, datetime

    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session_cm
    mock_session_cm.__aexit__.return_value = False

    mock_db_cm = AsyncMock()
    mock_db_cm.__aenter__.return_value = mock_db_cm
    mock_db_cm.__aexit__.return_value = False
    mock_db_cm.session_factory = MagicMock(return_value=mock_session_cm)
    mock_db_cls.return_value = mock_db_cm

    settlement = MagicMock()
    settlement.ticker = "TEST-TICKER"
    settlement.result = "yes"
    settlement.settled_at = datetime.now(UTC)

    mock_settlement_repo = MagicMock()
    mock_settlement_repo.get_settled_after = AsyncMock(return_value=[settlement])

    snapshot = MagicMock()
    snapshot.midpoint = 60

    mock_price_repo = MagicMock()
    mock_price_repo.get_for_market = AsyncMock(return_value=[snapshot])

    mock_result = MagicMock()
    mock_result.brier_score = 0.15
    mock_result.n_samples = 1
    mock_result.brier_skill_score = 0.4
    mock_result.resolution = 0.1
    mock_result.reliability = 0.05
    mock_result.uncertainty = 0.2

    mock_analyzer = MagicMock()
    mock_analyzer.compute_calibration.return_value = mock_result
    mock_analyzer_cls.return_value = mock_analyzer

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch(
            "kalshi_research.data.repositories.SettlementRepository",
            return_value=mock_settlement_repo,
        ),
        patch(
            "kalshi_research.data.repositories.PriceRepository",
            return_value=mock_price_repo,
        ),
    ):
        result = runner.invoke(app, ["analysis", "calibration"])

    assert result.exit_code == 0
    assert "Brier" in result.stdout or "0.15" in result.stdout


@patch("kalshi_research.data.DatabaseManager")
def test_analysis_metrics(mock_db_cls: MagicMock) -> None:
    mock_price = MagicMock()
    mock_price.yes_bid = 0
    mock_price.yes_ask = 2
    mock_price.no_bid = 48
    mock_price.no_ask = 50
    mock_price.volume_24h = 1000
    mock_price.open_interest = 500

    async def mock_get_latest(ticker):
        return mock_price

    mock_prices_repo = MagicMock()
    mock_prices_repo.get_latest = mock_get_latest

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()

    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = AsyncMock()
    mock_db.session_factory = mock_session_factory
    mock_db_cls.return_value = mock_db

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("kalshi_research.data.repositories.PriceRepository", return_value=mock_prices_repo),
    ):
        result = runner.invoke(app, ["analysis", "metrics", "TEST-TICKER"])

    assert result.exit_code == 0
    assert "TEST-TICKER" in result.stdout

    spread_row = next(line for line in result.stdout.splitlines() if "Spread" in line)
    assert "2¢" in spread_row
