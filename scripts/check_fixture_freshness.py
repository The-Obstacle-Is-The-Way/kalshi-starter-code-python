#!/usr/bin/env python3
"""
Check if golden fixtures are stale based on recorded timestamp.

This is a lightweight drift signal for scheduled CI:
- It does NOT re-record fixtures (requires API credentials).
- It warns (non-blocking in CI) when fixtures are older than the configured threshold.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

GOLDEN_DIR = Path("tests/fixtures/golden")
FRESHNESS_DAYS = 30


def _parse_recorded_at(recorded_at: str) -> datetime | None:
    try:
        return datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
    except ValueError:
        return None


def _debug(verbose: bool, message: str) -> None:
    if verbose:
        print(message, file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Warn if golden fixtures are older than N days.")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print debug info for fixtures skipped due to missing/invalid metadata.",
    )
    args = parser.parse_args(argv)

    if not GOLDEN_DIR.exists():
        print(f"ERROR: Golden fixtures directory not found: {GOLDEN_DIR}")
        return 2

    stale_fixtures: list[tuple[str, int]] = []
    now = datetime.now(UTC)
    verbose = args.verbose

    for fixture_path in GOLDEN_DIR.rglob("*.json"):
        if fixture_path.name.startswith("_"):
            continue

        try:
            data = json.loads(fixture_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            _debug(verbose, f"Skipping {fixture_path}: invalid JSON")
            continue

        if not isinstance(data, dict):
            _debug(verbose, f"Skipping {fixture_path}: root JSON is not an object")
            continue

        recorded_at = data.get("_metadata", {}).get("recorded_at")
        if not isinstance(recorded_at, str) or not recorded_at:
            _debug(verbose, f"Skipping {fixture_path}: missing _metadata.recorded_at")
            continue

        recorded_dt = _parse_recorded_at(recorded_at)
        if recorded_dt is None:
            _debug(
                verbose,
                f"Skipping {fixture_path}: invalid _metadata.recorded_at {recorded_at!r}",
            )
            continue

        age_days = (now - recorded_dt).days
        if age_days > FRESHNESS_DAYS:
            stale_fixtures.append((str(fixture_path.relative_to(GOLDEN_DIR)), age_days))

    if stale_fixtures:
        print(f"⚠️  {len(stale_fixtures)} fixtures older than {FRESHNESS_DAYS} days:")
        for name, age in sorted(stale_fixtures, key=lambda item: -item[1]):
            print(f"  - {name}: {age} days old")
        print("\nRe-record with:")
        print("  uv run python scripts/record_api_responses.py")
        print("  uv run python scripts/record_exa_responses.py")
        return 1

    print(f"✅ All fixtures are within {FRESHNESS_DAYS} days")
    return 0


if __name__ == "__main__":
    sys.exit(main())
