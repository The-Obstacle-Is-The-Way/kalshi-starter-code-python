#!/usr/bin/env python3
"""
Sanitize golden fixtures by replacing sensitive data with deterministic fake values.

This script replaces:
- user_id/order_id/trade_id/fill_id/client_order_id with stable fake UUIDs
- balance/portfolio_value with fixed example values
- tickers inside authenticated portfolio responses with synthetic placeholders
- selected money-like integer fields with stable example values

Run this BEFORE committing golden fixtures to a public repo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any, Final, Literal

GOLDEN_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "golden"

_SANITIZE_UUID_NAMESPACE: Final[uuid.UUID] = uuid.UUID("00000000-0000-0000-0000-000000000000")
_SANITIZE_SALT: Final[str] = "kalshi_research_sanitize_v1"

_UUID_LIKE_KEYS: Final[set[str]] = {
    "user_id",
    "order_id",
    "trade_id",
    "fill_id",
    "client_order_id",
    "updated_client_order_id",
    "order_group_id",
    # Order group detail response returns order IDs under `orders`.
    "orders",
}

_TICKER_KEYS: Final[set[str]] = {"ticker", "event_ticker", "series_ticker", "market_ticker"}

_FIXED_INT_OVERRIDES: Final[dict[str, int]] = {
    "balance": 10000,  # $100.00
    "portfolio_value": 25000,  # $250.00
}

# These are money-like values in authenticated portfolio responses (cents or cost-like ints).
_SANITIZE_INT_KEYS: Final[set[str]] = {
    "event_exposure",
    "fees_paid",
    "maker_fees",
    "maker_fill_cost",
    "market_exposure",
    "no_total_cost",
    "realized_pnl",
    "revenue",
    "taker_fees",
    "taker_fill_cost",
    "total_resting_order_value",
    "total_cost",
    "total_traded",
    "value",
    "yes_total_cost",
}

SanitizeResult = Literal["sanitized", "skipped", "failed"]


def _stable_int(text: str) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _fake_uuid(value: str) -> str:
    return str(uuid.uuid5(_SANITIZE_UUID_NAMESPACE, f"{_SANITIZE_SALT}:{value}"))


def _fake_ticker(value: str) -> str:
    suffix = hashlib.sha256(f"{_SANITIZE_SALT}:ticker:{value}".encode()).hexdigest()[:12].upper()
    return f"KXEXAMPLE-{suffix}"


def _cents_to_dollars_fixed(cents: int) -> str:
    return f"{(Decimal(cents) / Decimal(100)):.4f}"


def _fake_money_int(key: str, value: int) -> int:
    if value == 0:
        return 0
    sign = -1 if value < 0 else 1
    magnitude = abs(value)
    n = _stable_int(f"{_SANITIZE_SALT}:{key}:{magnitude}")
    return sign * (100 + (n % 50000))


def sanitize_value(key: str, value: object) -> object:
    """Sanitize a single value based on its key."""
    if value is None:
        return None

    # IDs - replace with stable fake UUID (even if original isn't UUID-shaped).
    if key in _UUID_LIKE_KEYS and isinstance(value, str) and value:
        return _fake_uuid(value)

    # Tickers - portfolio fixtures can leak trading interests/positions.
    if key in _TICKER_KEYS and isinstance(value, str) and value:
        return _fake_ticker(value)

    if key in _FIXED_INT_OVERRIDES and isinstance(value, int):
        return _FIXED_INT_OVERRIDES[key]

    if key in _SANITIZE_INT_KEYS and isinstance(value, int):
        return _fake_money_int(key, value)

    return value


def _normalize_dollars_pairs(data: dict[str, Any]) -> None:
    """
    Keep paired `<field>` and `<field>_dollars` values internally consistent.

    The API often returns both int-cent fields and fixed-point dollar strings.
    If we sanitize the int, we recompute the corresponding `_dollars` to match.
    """
    for key in list(data.keys()):
        if not key.endswith("_dollars"):
            continue
        base_key = key.removesuffix("_dollars")
        cents = data.get(base_key)
        if isinstance(cents, int):
            data[key] = _cents_to_dollars_fixed(cents)


def sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize a dictionary."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[key] = [
                sanitize_dict(item) if isinstance(item, dict) else sanitize_value(key, item)
                for item in value
            ]
        else:
            result[key] = sanitize_value(key, value)
    _normalize_dollars_pairs(result)
    return result


def _already_sanitized(data: object) -> bool:
    if not isinstance(data, dict):
        return False
    metadata = data.get("_metadata")
    return isinstance(metadata, dict) and metadata.get("sanitized") is True


def sanitize_file(filepath: Path, *, force: bool) -> SanitizeResult:
    """Sanitize a single golden fixture file."""
    try:
        data = json.loads(filepath.read_text())
        if _already_sanitized(data) and not force:
            return "skipped"
        if not isinstance(data, dict):
            raise ValueError("Golden fixture must be a JSON object.")

        sanitized = sanitize_dict(data)

        metadata = sanitized.get("_metadata")
        if isinstance(metadata, dict):
            metadata["sanitized"] = True
            sanitized_note = "Sensitive data replaced with example values"
            existing_note = metadata.get("note")
            if isinstance(existing_note, str) and existing_note.strip():
                if sanitized_note not in existing_note:
                    metadata["note"] = f"{existing_note}; {sanitized_note}"
            else:
                metadata["note"] = sanitized_note

        filepath.write_text(json.dumps(sanitized, indent=2))
        return "sanitized"
    except Exception as exc:
        print(f"Error sanitizing {filepath}: {exc}")
        return "failed"


def main() -> None:
    parser = argparse.ArgumentParser(description="Sanitize golden fixtures before committing")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-sanitize even if already marked sanitized (use when logic changes).",
    )
    args = parser.parse_args()

    print("Sanitizing golden fixtures...")
    print(f"Directory: {GOLDEN_DIR}\n")

    # Sanitize files containing sensitive data (user_id, order_id, balance, etc.)
    sensitive_files = [
        "portfolio_balance_response.json",
        "portfolio_positions_response.json",
        "portfolio_orders_response.json",
        "portfolio_fills_response.json",
        "portfolio_settlements_response.json",
        "portfolio_order_single_response.json",
        "portfolio_total_resting_order_value_response.json",
        "order_queue_position_response.json",
        "order_queue_positions_response.json",
        # Trading fixtures also contain user_id, order_id, client_order_id
        "create_order_response.json",
        "cancel_order_response.json",
        "amend_order_response.json",
        "batch_create_orders_response.json",
        "batch_cancel_orders_response.json",
        "decrease_order_response.json",
        # Order group fixtures (authenticated, demo-only)
        "order_group_create_response.json",
        "order_groups_list_response.json",
        "order_group_single_response.json",
        "order_group_reset_response.json",
        "order_group_delete_response.json",
    ]

    for filename in sensitive_files:
        filepath = GOLDEN_DIR / filename
        if not filepath.exists():
            print(f"Skipping (not found): {filename}")
            continue

        print(f"Sanitizing: {filename}")
        match sanitize_file(filepath, force=args.force):
            case "sanitized":
                print("  ✓ Done")
            case "skipped":
                print("  ↪ Skipped (already sanitized)")
            case "failed":
                print("  ✗ Failed")

    print("\n✓ Sanitization complete!")
    print("\nPublic fixtures (no changes needed):")
    for fixture in GOLDEN_DIR.glob("*.json"):
        if fixture.name not in sensitive_files and not fixture.name.startswith("_"):
            print(f"  {fixture.name}")


if __name__ == "__main__":
    main()
