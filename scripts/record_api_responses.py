#!/usr/bin/env python3
"""
Record actual API responses from Kalshi API as golden fixtures.

This script hits real endpoints and saves the response shapes as "golden fixtures".
These fixtures become the SSOT for what the API actually returns (not what docs say).

Usage:
    # Record all endpoints (requires API credentials)
    uv run python scripts/record_api_responses.py

    # Record specific endpoint category
    uv run python scripts/record_api_responses.py --endpoint markets

    # Override environment (default: from .env or prod)
    uv run python scripts/record_api_responses.py --env demo

Output:
    tests/fixtures/golden/<endpoint>_response.json

Note:
    All operations are READ-ONLY. Trading endpoints use dry_run=True.
    Run sanitize_golden_fixtures.py before committing to remove sensitive data.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from dotenv import load_dotenv

from kalshi_research.api.client import KalshiClient, KalshiPublicClient
from kalshi_research.api.config import Environment, get_config

load_dotenv()

GOLDEN_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "golden"


def save_golden(
    endpoint: str,
    data: dict[str, Any] | list[Any],
    metadata: dict[str, Any] | None = None,
) -> Path:
    """
    Save API response as golden fixture.

    Args:
        endpoint: API endpoint name (used to generate filename)
        data: Response data to save
        metadata: Optional metadata to include in fixture

    Returns:
        Path to the saved fixture file
    """
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{endpoint.replace('/', '_').strip('_')}_response.json"
    filepath = GOLDEN_DIR / filename

    output: dict[str, Any] = {
        "_metadata": {
            "recorded_at": datetime.now(UTC).isoformat(),
            "endpoint": endpoint,
            "environment": os.getenv("KALSHI_ENVIRONMENT", "prod"),
            **(metadata or {}),
        },
        "response": data,
    }

    filepath.write_text(json.dumps(output, indent=2, default=str))
    print(f"  Saved: {filepath}")
    return filepath


def _extract_first_market_ticker(raw_markets: dict[str, Any]) -> str | None:
    markets = raw_markets.get("markets")
    if not isinstance(markets, list) or not markets:
        return None
    first = markets[0]
    if not isinstance(first, dict):
        return None
    ticker = first.get("ticker")
    if not isinstance(ticker, str) or not ticker:
        return None
    return ticker


def _extract_first_event_ticker(raw_events: dict[str, Any]) -> str | None:
    events = raw_events.get("events")
    if not isinstance(events, list) or not events:
        return None
    first = events[0]
    if not isinstance(first, dict):
        return None
    event_ticker = first.get("event_ticker")
    if not isinstance(event_ticker, str) or not event_ticker:
        return None
    return event_ticker


async def _record_public_get(
    client: KalshiPublicClient,
    *,
    label: str,
    path: str,
    params: dict[str, Any] | None = None,
    save_as: str,
    metadata: dict[str, Any] | None = None,
    results: dict[str, Any],
) -> dict[str, Any] | None:
    print(f"Recording: {label}")
    try:
        raw = await client._get(path, params)
    except Exception as e:
        print(f"  ERROR: {e}")
        results[save_as] = {"error": str(e)}
        return None

    results[save_as] = raw
    save_golden(save_as, raw, metadata)
    return raw


async def _record_auth_get(
    client: KalshiClient,
    *,
    label: str,
    path: str,
    params: dict[str, Any] | None = None,
    save_as: str,
    metadata: dict[str, Any] | None = None,
    results: dict[str, Any],
) -> dict[str, Any] | None:
    print(f"Recording: {label}")
    try:
        raw = await client._auth_get(path, params)
    except Exception as e:
        print(f"  ERROR: {e}")
        results[save_as] = {"error": str(e)}
        return None

    results[save_as] = raw
    save_golden(save_as, raw, metadata)
    return raw


async def record_public_endpoints() -> dict[str, Any]:
    """Record responses from public (unauthenticated) endpoints."""
    results: dict[str, Any] = {}

    async with KalshiPublicClient() as client:
        print("\n=== PUBLIC ENDPOINTS ===\n")

        raw_markets = await _record_public_get(
            client,
            label="GET /markets (RAW)",
            path="/markets",
            params={"limit": 5, "status": "open"},
            save_as="markets_list",
            metadata={"limit": 5, "status": "open", "note": "RAW API response (SSOT)"},
            results=results,
        )

        first_ticker = _extract_first_market_ticker(raw_markets or {})
        if first_ticker:
            await _record_public_get(
                client,
                label=f"GET /markets/{first_ticker} (RAW)",
                path=f"/markets/{first_ticker}",
                save_as="market_single",
                metadata={"ticker": first_ticker, "note": "RAW API response (SSOT)"},
                results=results,
            )
            await _record_public_get(
                client,
                label=f"GET /markets/{first_ticker}/orderbook (RAW)",
                path=f"/markets/{first_ticker}/orderbook",
                save_as="orderbook",
                metadata={"ticker": first_ticker, "note": "RAW API response (SSOT)"},
                results=results,
            )

        raw_events = await _record_public_get(
            client,
            label="GET /events (RAW)",
            path="/events",
            params={"limit": 5},
            save_as="events_list",
            metadata={"limit": 5, "note": "RAW API response (SSOT)"},
            results=results,
        )

        first_event_ticker = _extract_first_event_ticker(raw_events or {})
        if first_event_ticker:
            await _record_public_get(
                client,
                label=f"GET /events/{first_event_ticker} (RAW)",
                path=f"/events/{first_event_ticker}",
                save_as="event_single",
                metadata={"ticker": first_event_ticker, "note": "RAW API response (SSOT)"},
                results=results,
            )

        await _record_public_get(
            client,
            label="GET /exchange/status (RAW)",
            path="/exchange/status",
            save_as="exchange_status",
            metadata={"note": "RAW API response (SSOT)"},
            results=results,
        )

    return results


async def record_authenticated_endpoints() -> dict[str, Any]:
    """Record responses from authenticated endpoints (portfolio, orders)."""
    config = get_config()
    results: dict[str, Any] = {}

    key_id = os.getenv("KALSHI_KEY_ID")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH")
    private_key_b64 = os.getenv("KALSHI_PRIVATE_KEY_B64")

    if not key_id:
        print("\n=== AUTHENTICATED ENDPOINTS ===\n")
        print("  SKIPPED: No KALSHI_KEY_ID configured")
        return results

    try:
        async with KalshiClient(
            key_id=key_id,
            private_key_path=private_key_path,
            private_key_b64=private_key_b64,
            environment=config.environment,
        ) as client:
            print("\n=== AUTHENTICATED ENDPOINTS ===\n")

            await _record_auth_get(
                client,
                label="GET /portfolio/balance",
                path="/portfolio/balance",
                save_as="portfolio_balance",
                metadata={"note": "RAW API response (SSOT)"},
                results=results,
            )
            await _record_auth_get(
                client,
                label="GET /portfolio/positions",
                path="/portfolio/positions",
                save_as="portfolio_positions",
                metadata={"note": "RAW API response (SSOT)"},
                results=results,
            )
            await _record_auth_get(
                client,
                label="GET /portfolio/orders",
                path="/portfolio/orders",
                params={"limit": 5},
                save_as="portfolio_orders",
                metadata={"limit": 5, "note": "RAW API response (SSOT)"},
                results=results,
            )
            await _record_auth_get(
                client,
                label="GET /portfolio/fills",
                path="/portfolio/fills",
                params={"limit": 5},
                save_as="portfolio_fills",
                metadata={"limit": 5, "note": "RAW API response (SSOT)"},
                results=results,
            )
            await _record_auth_get(
                client,
                label="GET /portfolio/settlements",
                path="/portfolio/settlements",
                params={"limit": 5},
                save_as="portfolio_settlements",
                metadata={"limit": 5, "note": "RAW API response (SSOT)"},
                results=results,
            )

    except Exception as e:
        print(f"\n  AUTH ERROR: {e}")
        results["auth_error"] = str(e)

    return results


async def record_trading_dry_run() -> dict[str, Any]:
    """Record trading endpoint responses using dry_run mode (NO REAL ORDERS)."""
    config = get_config()
    results: dict[str, Any] = {}

    key_id = os.getenv("KALSHI_KEY_ID")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH")
    private_key_b64 = os.getenv("KALSHI_PRIVATE_KEY_B64")

    if not key_id:
        print("\n=== TRADING ENDPOINTS (DRY RUN) ===\n")
        print("  SKIPPED: No KALSHI_KEY_ID configured")
        return results

    # Only run on demo to be extra safe
    if config.environment != Environment.DEMO:
        print("\n=== TRADING ENDPOINTS (DRY RUN) ===\n")
        print("  SKIPPED: Only runs on demo environment for safety")
        print("  Set KALSHI_ENVIRONMENT=demo to record trading responses")
        return results

    try:
        async with KalshiClient(
            key_id=key_id,
            private_key_path=private_key_path,
            private_key_b64=private_key_b64,
            environment=config.environment,
        ) as client:
            print("\n=== TRADING ENDPOINTS (DRY RUN) ===\n")

            # Get a real market ticker for the test
            markets, _ = await client.get_markets_page(limit=1, status="open")
            if not markets:
                print("  SKIPPED: No open markets found")
                return results

            ticker = markets[0].ticker
            print(f"  Using ticker: {ticker}")

            print("Recording: POST /portfolio/orders (DRY RUN)")
            try:
                order_response = await client.create_order(
                    ticker=ticker,
                    side="yes",
                    action="buy",
                    count=1,
                    price=1,  # 1 cent - minimum
                    dry_run=True,
                )
                results["create_order_dry_run"] = order_response.model_dump(mode="json")
                save_golden(
                    "create_order_response",
                    results["create_order_dry_run"],
                    {
                        "ticker": ticker,
                        "dry_run": True,
                        "note": "DRY RUN - simulated, not real API",
                    },
                )
                print("  NOTE: dry_run returns simulated response, not actual API shape!")
            except Exception as e:
                print(f"  ERROR: {e}")
                results["create_order_dry_run"] = {"error": str(e)}

    except Exception as e:
        print(f"\n  TRADING ERROR: {e}")
        results["trading_error"] = str(e)

    return results


async def main() -> None:
    parser = argparse.ArgumentParser(description="Record actual API responses as golden fixtures")
    parser.add_argument(
        "--env",
        choices=["demo", "prod"],
        default=None,
        help="Override KALSHI_ENVIRONMENT (default: use .env value)",
    )
    parser.add_argument(
        "--endpoint",
        choices=["public", "authenticated", "trading", "all"],
        default="all",
        help="Which endpoints to record",
    )
    args = parser.parse_args()

    if args.env:
        os.environ["KALSHI_ENVIRONMENT"] = args.env

    env = os.getenv("KALSHI_ENVIRONMENT", "prod")
    print(f"\n{'=' * 60}")
    print(f"RECORDING API RESPONSES FROM: {env.upper()}")
    print(f"{'=' * 60}")

    if env == "prod":
        print("\nWARNING: Using PRODUCTION API")
        print("All operations are READ-ONLY, but be aware this hits real API.")
        response = input("Continue? [y/N]: ")
        if response.lower() != "y":
            print("Aborted.")
            return

    all_results: dict[str, Any] = {}

    if args.endpoint in ("public", "all"):
        all_results["public"] = await record_public_endpoints()

    if args.endpoint in ("authenticated", "all"):
        all_results["authenticated"] = await record_authenticated_endpoints()

    if args.endpoint in ("trading", "all"):
        all_results["trading"] = await record_trading_dry_run()

    # Save summary
    summary_path = GOLDEN_DIR / "_recording_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "recorded_at": datetime.now().isoformat(),
                "environment": env,
                "endpoints_recorded": list(all_results.keys()),
                "golden_dir": str(GOLDEN_DIR),
            },
            indent=2,
        )
    )

    print(f"\n{'=' * 60}")
    print(f"DONE! Golden fixtures saved to: {GOLDEN_DIR}")
    print(f"{'=' * 60}\n")

    # Show what was recorded
    print("Files created:")
    for f in sorted(GOLDEN_DIR.glob("*.json")):
        print(f"  {f.name}")


if __name__ == "__main__":
    asyncio.run(main())
