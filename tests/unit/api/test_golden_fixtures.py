from __future__ import annotations

from kalshi_research.api.models.candlestick import Candlestick, CandlestickResponse
from kalshi_research.api.models.trade import Trade
from tests.golden_fixtures import load_golden_response


def test_trade_fixture_matches_model() -> None:
    response = load_golden_response("trades_list_response.json")
    Trade.model_validate(response["trades"][0])


def test_batch_candlesticks_fixture_matches_model() -> None:
    response = load_golden_response("candlesticks_batch_response.json")
    CandlestickResponse.model_validate(response["markets"][0])


def test_series_candlesticks_fixture_matches_model() -> None:
    response = load_golden_response("series_candlesticks_response.json")
    Candlestick.model_validate(response["candlesticks"][0])
