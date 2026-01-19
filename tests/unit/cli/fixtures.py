from __future__ import annotations

from typing import Any

from tests.golden_fixtures import load_golden_response

KALSHI_PROD_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
KALSHI_DEMO_BASE_URL = "https://demo-api.kalshi.co/trade-api/v2"


def load_market_fixture() -> dict[str, Any]:
    return load_golden_response("market_single_response.json")


def load_markets_list_fixture() -> dict[str, Any]:
    return load_golden_response("markets_list_response.json")


def load_events_list_fixture() -> dict[str, Any]:
    return load_golden_response("events_list_response.json")


def load_event_single_fixture() -> dict[str, Any]:
    return load_golden_response("event_single_response.json")


def load_event_metadata_fixture() -> dict[str, Any]:
    return load_golden_response("event_metadata_response.json")


def load_event_candlesticks_fixture() -> dict[str, Any]:
    return load_golden_response("event_candlesticks_response.json")


def load_orderbook_fixture() -> dict[str, Any]:
    return load_golden_response("orderbook_response.json")


def load_candlesticks_batch_fixture() -> dict[str, Any]:
    return load_golden_response("candlesticks_batch_response.json")


def load_series_candlesticks_fixture() -> dict[str, Any]:
    return load_golden_response("series_candlesticks_response.json")


def load_exchange_status_fixture() -> dict[str, Any]:
    return load_golden_response("exchange_status_response.json")


def load_exchange_schedule_fixture() -> dict[str, Any]:
    return load_golden_response("exchange_schedule_response.json")


def load_exchange_announcements_fixture() -> dict[str, Any]:
    return load_golden_response("exchange_announcements_response.json")


def load_tags_by_categories_fixture() -> dict[str, Any]:
    return load_golden_response("tags_by_categories_response.json")


def load_filters_by_sport_fixture() -> dict[str, Any]:
    return load_golden_response("filters_by_sport_response.json")


def load_series_list_fixture() -> dict[str, Any]:
    return load_golden_response("series_list_response.json")


def load_series_single_fixture() -> dict[str, Any]:
    return load_golden_response("series_single_response.json")


def load_multivariate_events_fixture() -> dict[str, Any]:
    return load_golden_response("events_multivariate_list_response.json")


def load_multivariate_event_collections_fixture() -> dict[str, Any]:
    return load_golden_response("multivariate_event_collections_list_response.json")


def load_multivariate_event_collection_fixture() -> dict[str, Any]:
    return load_golden_response("multivariate_event_collection_single_response.json")


def load_portfolio_balance_fixture() -> dict[str, Any]:
    return load_golden_response("portfolio_balance_response.json")
