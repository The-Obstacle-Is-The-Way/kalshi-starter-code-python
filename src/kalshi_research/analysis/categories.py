"""Market category classification helpers.

These utilities support CLI filtering when the Kalshi Market response no longer includes a
`category` field. We rely on event tickers as a lightweight signal and provide aliases for
human-friendly CLI input.

Category names match Kalshi's official categories as observed on the Events endpoint.
"""

from __future__ import annotations

OTHER_CATEGORY = "Other"

# Keys match Kalshi's official category names from GET /events.
CATEGORY_PATTERNS: dict[str, list[str]] = {
    "Politics": [
        "KXTRUMP",
        "KXBIDEN",
        "KXCONGRESS",
        "KXSENATE",
        "KXHOUSE",
        "KXGOV",
        "KXPRES",
        "KXELECT",
        "KXPOTUS",
        "KXVP",
    ],
    "Economics": [
        "KXFED",
        "KXCPI",
        "KXGDP",
        "KXJOBS",
        "KXUNEMPLOY",
        "KXRECESSION",
        "KXRATE",
        "KXINFLATION",
        "KXSP500",
    ],
    "Financials": ["KXBTC", "KXETH", "KXCRYPTO", "KXBITCOIN"],
    "Science and Technology": ["KXOAI", "KXANTH", "KXGOOGLE", "KXAI", "KXCHATGPT"],
    "Sports": [
        "KXNFL",
        "KXNBA",
        "KXMLB",
        "KXNCAA",
        "KXSB",
        "KXMVE",
        "KXNHL",
        "KXSOCCER",
        "KXTENNIS",
        "KXGOLF",
    ],
    "Entertainment": ["KXOSCAR", "KXEMMY", "KXGOLDEN", "KXMOVIE"],
    "Climate and Weather": ["KXWEATHER", "KXHURRICANE", "KXTEMP", "KXWARMING"],
    "World": ["KXWAR", "KXCONFLICT", "KXGEOPOL", "KXELONMARS", "KXNEWPOPE"],
}

# CLI-friendly aliases (case-insensitive).
CATEGORY_ALIASES: dict[str, str] = {
    "politics": "Politics",
    "pol": "Politics",
    "economics": "Economics",
    "econ": "Economics",
    "financials": "Financials",
    "finance": "Financials",
    "crypto": "Financials",
    "tech": "Science and Technology",
    "science": "Science and Technology",
    "ai": "Science and Technology",
    "sports": "Sports",
    "entertainment": "Entertainment",
    "climate": "Climate and Weather",
    "weather": "Climate and Weather",
    "world": "World",
}


def normalize_category(user_input: str) -> str:
    """Normalize user input to an official Kalshi category name."""
    lower = user_input.strip().lower()
    return CATEGORY_ALIASES.get(lower, user_input)


def classify_by_event_ticker(event_ticker: str) -> str:
    """Classify a market's category by its event ticker prefix."""
    upper = event_ticker.strip().upper()
    for category, patterns in CATEGORY_PATTERNS.items():
        if any(upper.startswith(pattern) for pattern in patterns):
            return category
    return OTHER_CATEGORY


def get_category_patterns(category: str) -> list[str]:
    """Get event ticker patterns for a (normalized) category."""
    normalized = normalize_category(category)
    return CATEGORY_PATTERNS.get(normalized, [])


def list_categories() -> list[str]:
    """List available official categories."""
    return list(CATEGORY_PATTERNS.keys())
