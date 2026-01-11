from kalshi_research.analysis.categories import (
    classify_by_event_ticker,
    list_categories,
    normalize_category,
)


def test_normalize_category_supports_common_aliases() -> None:
    assert normalize_category("ai") == "Science and Technology"
    assert normalize_category("tech") == "Science and Technology"
    assert normalize_category("pol") == "Politics"
    assert normalize_category("econ") == "Economics"
    assert normalize_category("crypto") == "Financials"
    assert normalize_category("weather") == "Climate and Weather"


def test_normalize_category_accepts_official_names_case_insensitively() -> None:
    assert normalize_category("science and technology") == "Science and Technology"
    assert normalize_category(" Science and Technology ") == "Science and Technology"
    assert normalize_category("CLIMATE AND WEATHER") == "Climate and Weather"


def test_normalize_category_returns_stripped_input_for_unknown_category() -> None:
    assert normalize_category("  Unknown Category  ") == "Unknown Category"


def test_classify_by_event_ticker_matches_known_prefixes() -> None:
    assert classify_by_event_ticker("KXFED-26JAN") == "Economics"
    assert classify_by_event_ticker("kxnfl-26JAN") == "Sports"
    assert classify_by_event_ticker("KXOAI-26JAN") == "Science and Technology"


def test_classify_by_event_ticker_falls_back_to_other() -> None:
    assert classify_by_event_ticker("KXUNKNOWN-26JAN") == "Other"


def test_list_categories_contains_expected_official_names() -> None:
    categories = set(list_categories())
    assert "Politics" in categories
    assert "Economics" in categories
    assert "Science and Technology" in categories
