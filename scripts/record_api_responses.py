#!/usr/bin/env python3
"""
Record actual API responses from Kalshi API as golden fixtures.

This script hits real endpoints and saves the response shapes as "golden fixtures".
These fixtures become the SSOT for what the API actually returns (not what docs say).

Usage:
    # Record all endpoints (requires API credentials)
    uv run python scripts/record_api_responses.py

    # Record specific endpoint category
    uv run python scripts/record_api_responses.py --endpoint public

    # Override environment (default: from .env or prod)
    uv run python scripts/record_api_responses.py --env demo

Output:
    tests/fixtures/golden/<endpoint>_response.json

Note:
    All operations are READ-ONLY.
    Run sanitize_golden_fixtures.py before committing to remove sensitive data.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from dotenv import load_dotenv

from kalshi_research.api.client import KalshiClient, KalshiPublicClient
from kalshi_research.api.config import get_config

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
            "sanitized": False,
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


def _extract_first_market_ticker_from_event_single(raw_event_single: dict[str, Any]) -> str | None:
    markets = raw_event_single.get("markets")
    if not isinstance(markets, list) or not markets:
        return None
    first = markets[0]
    if not isinstance(first, dict):
        return None
    ticker = first.get("ticker")
    if not isinstance(ticker, str) or not ticker:
        return None
    return ticker


def _extract_series_ticker_from_event_single(raw_event_single: dict[str, Any]) -> str | None:
    event = raw_event_single.get("event")
    if not isinstance(event, dict):
        return None
    series_ticker = event.get("series_ticker")
    if not isinstance(series_ticker, str) or not series_ticker:
        return None
    return series_ticker


def _batch_candlesticks_has_data(raw_batch: dict[str, Any]) -> bool:
    markets = raw_batch.get("markets")
    if not isinstance(markets, list) or not markets:
        return False
    first = markets[0]
    if not isinstance(first, dict):
        return False
    candlesticks = first.get("candlesticks")
    return isinstance(candlesticks, list) and len(candlesticks) > 0


def _series_candlesticks_has_data(raw_series: dict[str, Any]) -> bool:
    candlesticks = raw_series.get("candlesticks")
    return isinstance(candlesticks, list) and len(candlesticks) > 0


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
            raw_event_single = await _record_public_get(
                client,
                label=f"GET /events/{first_event_ticker} (RAW)",
                path=f"/events/{first_event_ticker}",
                save_as="event_single",
                metadata={"ticker": first_event_ticker, "note": "RAW API response (SSOT)"},
                results=results,
            )

            market_ticker = _extract_first_market_ticker_from_event_single(raw_event_single or {})
            series_ticker = _extract_series_ticker_from_event_single(raw_event_single or {})
            if market_ticker:
                await _record_public_get(
                    client,
                    label=f"GET /markets/trades?ticker={market_ticker} (RAW)",
                    path="/markets/trades",
                    params={"ticker": market_ticker, "limit": 5},
                    save_as="trades_list",
                    metadata={
                        "ticker": market_ticker,
                        "limit": 5,
                        "note": "RAW API response (SSOT)",
                    },
                    results=results,
                )

                now_ts = int(datetime.now(UTC).timestamp())
                start_ts_short = now_ts - 90 * 24 * 60 * 60
                start_ts_long = now_ts - 365 * 24 * 60 * 60

                raw_batch = await _record_public_get(
                    client,
                    label=f"GET /markets/candlesticks?market_tickers={market_ticker} (RAW)",
                    path="/markets/candlesticks",
                    params={
                        "market_tickers": market_ticker,
                        "start_ts": start_ts_short,
                        "end_ts": now_ts,
                        "period_interval": 1440,
                    },
                    save_as="candlesticks_batch",
                    metadata={
                        "market_tickers": [market_ticker],
                        "start_ts": start_ts_short,
                        "end_ts": now_ts,
                        "period_interval": 1440,
                        "note": "RAW API response (SSOT) - daily candles (90d)",
                    },
                    results=results,
                )

                if raw_batch is not None and not _batch_candlesticks_has_data(raw_batch):
                    await _record_public_get(
                        client,
                        label=(
                            f"GET /markets/candlesticks?market_tickers={market_ticker} "
                            "(RAW, retry 365d)"
                        ),
                        path="/markets/candlesticks",
                        params={
                            "market_tickers": market_ticker,
                            "start_ts": start_ts_long,
                            "end_ts": now_ts,
                            "period_interval": 1440,
                        },
                        save_as="candlesticks_batch",
                        metadata={
                            "market_tickers": [market_ticker],
                            "start_ts": start_ts_long,
                            "end_ts": now_ts,
                            "period_interval": 1440,
                            "note": "RAW API response (SSOT) - daily candles (365d retry)",
                        },
                        results=results,
                    )

                if series_ticker:
                    raw_series = await _record_public_get(
                        client,
                        label=(
                            f"GET /series/{series_ticker}/markets/{market_ticker}/candlesticks "
                            "(RAW)"
                        ),
                        path=f"/series/{series_ticker}/markets/{market_ticker}/candlesticks",
                        params={
                            "period_interval": 1440,
                            "start_ts": start_ts_short,
                            "end_ts": now_ts,
                        },
                        save_as="series_candlesticks",
                        metadata={
                            "series_ticker": series_ticker,
                            "ticker": market_ticker,
                            "start_ts": start_ts_short,
                            "end_ts": now_ts,
                            "period_interval": 1440,
                            "note": "RAW API response (SSOT) - daily candles (90d)",
                        },
                        results=results,
                    )

                    if raw_series is not None and not _series_candlesticks_has_data(raw_series):
                        await _record_public_get(
                            client,
                            label=(
                                f"GET /series/{series_ticker}/markets/{market_ticker}/candlesticks "
                                "(RAW, retry 365d)"
                            ),
                            path=f"/series/{series_ticker}/markets/{market_ticker}/candlesticks",
                            params={
                                "period_interval": 1440,
                                "start_ts": start_ts_long,
                                "end_ts": now_ts,
                            },
                            save_as="series_candlesticks",
                            metadata={
                                "series_ticker": series_ticker,
                                "ticker": market_ticker,
                                "start_ts": start_ts_long,
                                "end_ts": now_ts,
                                "period_interval": 1440,
                                "note": "RAW API response (SSOT) - daily candles (365d retry)",
                            },
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
            environment=config.environment.value,
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
        choices=["public", "authenticated", "all"],
        default="all",
        help="Which endpoints to record",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the production confirmation prompt (non-interactive safe).",
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
        if not args.yes:
            if not sys.stdin.isatty():
                print("Refusing to record from prod in non-interactive mode without --yes.")
                return
            response = input("Continue? [y/N]: ")
            if response.lower() != "y":
                print("Aborted.")
                return

    all_results: dict[str, Any] = {}

    if args.endpoint in ("public", "all"):
        all_results["public"] = await record_public_endpoints()

    if args.endpoint in ("authenticated", "all"):
        all_results["authenticated"] = await record_authenticated_endpoints()

    # Save summary
    summary_path = GOLDEN_DIR / "_recording_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "_metadata": {
                    "recorded_at": datetime.now(UTC).isoformat(),
                    "endpoint": "_recording_summary",
                    "environment": env,
                },
                "response": {
                    "environment": env,
                    "endpoints_recorded": list(all_results.keys()),
                },
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
