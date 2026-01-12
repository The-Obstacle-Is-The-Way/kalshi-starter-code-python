#!/usr/bin/env python3
"""
Sanitize golden fixtures by replacing sensitive data with fake values.

This script replaces:
- user_id with a fake UUID
- Actual balance/portfolio values with example values
- Real order_ids with fake UUIDs
- Real trade_ids/fill_ids with fake UUIDs

Run this BEFORE committing golden fixtures to public repo.
"""

import json
import re
import uuid
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "golden"

# Mapping of real values to sanitized values (for consistency)
UUID_MAP: dict[str, str] = {}


def get_fake_uuid(real_uuid: str) -> str:
    """Generate consistent fake UUID for a real one."""
    if real_uuid not in UUID_MAP:
        UUID_MAP[real_uuid] = str(uuid.uuid4())
    return UUID_MAP[real_uuid]


def sanitize_value(key: str, value: object) -> object:
    """Sanitize a single value based on its key."""
    if value is None:
        return None

    # UUIDs - replace with fake
    if (
        key in ("user_id", "order_id", "trade_id", "fill_id", "client_order_id")
        and isinstance(value, str)
        and value
        and re.match(r"^[a-f0-9-]{36}$", value)
    ):
        return get_fake_uuid(value)

    # Balance - use example values
    if key == "balance":
        return 10000  # $100.00

    if key == "portfolio_value":
        return 25000  # $250.00

    # Exposure/cost values - randomize slightly
    if (
        key in ("market_exposure", "taker_fill_cost", "maker_fill_cost")
        and isinstance(value, int)
        and value > 0
    ):
        return 1000 + (hash(str(value)) % 5000)  # Random-ish but deterministic

    return value


def sanitize_dict(data: dict) -> dict:
    """Recursively sanitize a dictionary."""
    result = {}
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
    return result


def sanitize_file(filepath: Path) -> bool:
    """Sanitize a single golden fixture file."""
    try:
        data = json.loads(filepath.read_text())
        sanitized = sanitize_dict(data)

        # Update metadata to note sanitization
        if "_metadata" in sanitized:
            sanitized["_metadata"]["sanitized"] = True
            sanitized["_metadata"]["note"] = "Sensitive data replaced with example values"

        filepath.write_text(json.dumps(sanitized, indent=2))
        return True
    except Exception as e:
        print(f"Error sanitizing {filepath}: {e}")
        return False


def main():
    print("Sanitizing golden fixtures...")
    print(f"Directory: {GOLDEN_DIR}\n")

    # Only sanitize portfolio files (they contain sensitive data)
    sensitive_files = [
        "portfolio_balance_response.json",
        "portfolio_positions_response.json",
        "portfolio_orders_response.json",
        "portfolio_fills_response.json",
        "portfolio_settlements_response.json",
    ]

    for filename in sensitive_files:
        filepath = GOLDEN_DIR / filename
        if filepath.exists():
            print(f"Sanitizing: {filename}")
            if sanitize_file(filepath):
                print("  ✓ Done")
            else:
                print("  ✗ Failed")
        else:
            print(f"Skipping (not found): {filename}")

    print("\n✓ Sanitization complete!")
    print("\nPublic fixtures (no changes needed):")
    for f in GOLDEN_DIR.glob("*.json"):
        if f.name not in sensitive_files and not f.name.startswith("_"):
            print(f"  {f.name}")


if __name__ == "__main__":
    main()
