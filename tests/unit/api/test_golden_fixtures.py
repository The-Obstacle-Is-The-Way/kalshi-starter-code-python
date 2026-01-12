from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kalshi_research.api.models.candlestick import Candlestick, CandlestickResponse
from kalshi_research.api.models.trade import Trade


def _load_golden_fixture(name: str) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    fixture_path = root / "tests" / "fixtures" / "golden" / name
    data = json.loads(fixture_path.read_text())
    return data["response"]


def test_trade_fixture_matches_model() -> None:
    response = _load_golden_fixture("trades_list_response.json")
    Trade.model_validate(response["trades"][0])


def test_batch_candlesticks_fixture_matches_model() -> None:
    response = _load_golden_fixture("candlesticks_batch_response.json")
    CandlestickResponse.model_validate(response["markets"][0])


def test_series_candlesticks_fixture_matches_model() -> None:
    response = _load_golden_fixture("series_candlesticks_response.json")
    Candlestick.model_validate(response["candlesticks"][0])
