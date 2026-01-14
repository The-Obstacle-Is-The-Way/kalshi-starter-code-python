from __future__ import annotations

from kalshi_research.api.models.candlestick import Candlestick, CandlestickResponse
from kalshi_research.api.models.event import Event
from kalshi_research.api.models.search import TagsByCategoriesResponse
from kalshi_research.api.models.series import Series, SeriesFeeChangesResponse
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


def test_tags_by_categories_fixture_matches_model() -> None:
    response = load_golden_response("tags_by_categories_response.json")
    TagsByCategoriesResponse.model_validate(response)


def test_series_list_fixture_matches_model() -> None:
    response = load_golden_response("series_list_response.json")
    series = response.get("series")
    if not isinstance(series, list) or not series:
        raise AssertionError("Expected non-empty series list in series_list_response.json")
    Series.model_validate(series[0])


def test_series_single_fixture_matches_model() -> None:
    response = load_golden_response("series_single_response.json")
    Series.model_validate(response["series"])


def test_series_fee_changes_fixture_matches_model() -> None:
    response = load_golden_response("series_fee_changes_response.json")
    SeriesFeeChangesResponse.model_validate(response)


def test_events_multivariate_fixture_matches_model() -> None:
    response = load_golden_response("events_multivariate_list_response.json")
    events = response.get("events")
    if not isinstance(events, list) or not events:
        raise AssertionError(
            "Expected non-empty events list in events_multivariate_list_response.json"
        )
    Event.model_validate(events[0])
