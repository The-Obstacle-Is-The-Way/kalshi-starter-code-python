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
    Public + portfolio recordings are read-only.

    Order write fixtures (create/cancel/amend/batch/decrease) require explicit opt-in and MUST
    be recorded from the demo environment:
        uv run python scripts/record_api_responses.py --env demo --endpoint authenticated
            --include-writes

    Run sanitize_golden_fixtures.py before committing to remove sensitive data.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from dotenv import load_dotenv

from kalshi_research.api.client import KalshiClient, KalshiPublicClient
from kalshi_research.api.config import Environment, get_config, set_environment
from kalshi_research.api.credentials import get_kalshi_auth_env_var_names, resolve_kalshi_auth_env
from kalshi_research.api.exceptions import KalshiAPIError

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


def _extract_first_series_ticker(raw_series_list: dict[str, Any]) -> str | None:
    series = raw_series_list.get("series")
    if not isinstance(series, list) or not series:
        return None
    first = series[0]
    if not isinstance(first, dict):
        return None
    ticker = first.get("ticker")
    if not isinstance(ticker, str) or not ticker:
        return None
    return ticker


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


async def _auth_request_raw(
    client: KalshiClient,
    *,
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    batch_size: int = 0,
) -> dict[str, Any]:
    method_upper = method.strip().upper()
    await client._rate_limiter.acquire(method_upper, path, batch_size=batch_size)

    full_path = client.API_PATH + path
    headers = client._auth.get_headers(method_upper, full_path)

    response = await client._client.request(
        method_upper,
        path,
        params=params,
        json=json_body,
        headers=headers,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text}")

    payload = response.json()
    if not isinstance(payload, dict):
        raise TypeError(f"Unexpected response type: {type(payload)!r} (expected JSON object)")
    return payload


async def _record_auth_request(
    client: KalshiClient,
    *,
    label: str,
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    batch_size: int = 0,
    save_as: str,
    metadata: dict[str, Any] | None = None,
    results: dict[str, Any],
) -> dict[str, Any] | None:
    print(f"Recording: {label}")
    try:
        raw = await _auth_request_raw(
            client,
            method=method,
            path=path,
            params=params,
            json_body=json_body,
            batch_size=batch_size,
        )
    except Exception as e:
        print(f"  ERROR: {e}")
        results[save_as] = {"error": str(e)}
        return None

    results[save_as] = raw
    save_golden(save_as, raw, metadata)
    return raw


def _select_market_for_order_writes(raw_markets: dict[str, Any]) -> tuple[str, int, int] | None:
    markets = raw_markets.get("markets")
    if not isinstance(markets, list) or not markets:
        return None

    for market in markets:
        if not isinstance(market, dict):
            continue
        ticker = market.get("ticker")
        if not isinstance(ticker, str) or not ticker:
            continue
        status = market.get("status")
        if status not in {"active"}:
            continue
        yes_ask = market.get("yes_ask")
        if not isinstance(yes_ask, int) or not (2 <= yes_ask <= 99):
            continue

        yes_bid = market.get("yes_bid")
        yes_bid_int = yes_bid if isinstance(yes_bid, int) else 0
        # Ensure this order cannot cross the spread.
        safe_price = max(1, min(yes_bid_int, yes_ask - 1))
        if safe_price >= yes_ask:
            continue
        return ticker, safe_price, yes_ask

    return None


async def _record_series_discovery_endpoints(
    client: KalshiPublicClient,
    *,
    raw_tags_by_categories: dict[str, Any] | None,
    results: dict[str, Any],
) -> None:
    """
    Record discovery endpoints that support category->series browsing.

    We derive a real category from the `/search/tags_by_categories` response to keep the
    `/series` fixture representative and reasonably sized.
    """
    # Record series discovery endpoints (category derived from tags_by_categories).
    tags_map: object | None = None
    if isinstance(raw_tags_by_categories, dict):
        tags_map = raw_tags_by_categories.get("tags_by_categories")

    category_candidates: list[str] = []
    if isinstance(tags_map, dict):
        category_candidates = [
            category
            for category, tags in tags_map.items()
            if isinstance(category, str)
            and category
            and isinstance(tags, list)
            and any(isinstance(tag, str) and tag for tag in tags)
        ]

    chosen_category: str | None = category_candidates[0] if category_candidates else None

    raw_series_list: dict[str, Any] | None = None
    if chosen_category is not None:
        try:
            raw_series_list = await client._get("/series", params={"category": chosen_category})
            results["series_list"] = raw_series_list
            save_golden(
                "series_list",
                raw_series_list,
                {
                    "category": chosen_category,
                    "note": "RAW API response (SSOT)",
                },
            )
        except Exception as exc:
            print(f"  ERROR recording /series: {exc}")
            raw_series_list = None
    else:
        print(
            "  SKIP recording /series: no categories found in /search/tags_by_categories response"
        )

    series_ticker = _extract_first_series_ticker(raw_series_list or {})
    if series_ticker:
        await _record_public_get(
            client,
            label=f"GET /series/{series_ticker} (RAW)",
            path=f"/series/{series_ticker}",
            save_as="series_single",
            metadata={"series_ticker": series_ticker, "note": "RAW API response (SSOT)"},
            results=results,
        )

    await _record_public_get(
        client,
        label="GET /series/fee_changes (RAW)",
        path="/series/fee_changes",
        save_as="series_fee_changes",
        metadata={"note": "RAW API response (SSOT)"},
        results=results,
    )


async def record_public_endpoints() -> dict[str, Any]:
    """Record responses from public (unauthenticated) endpoints."""
    results: dict[str, Any] = {}

    async with KalshiPublicClient() as client:
        print("\n=== PUBLIC ENDPOINTS ===\n")

        raw_tags_by_categories = await _record_public_get(
            client,
            label="GET /search/tags_by_categories (RAW)",
            path="/search/tags_by_categories",
            save_as="tags_by_categories",
            metadata={"note": "RAW API response (SSOT)"},
            results=results,
        )

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

        await _record_public_get(
            client,
            label="GET /events/multivariate (RAW)",
            path="/events/multivariate",
            params={"limit": 5},
            save_as="events_multivariate_list",
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

        await _record_series_discovery_endpoints(
            client,
            raw_tags_by_categories=raw_tags_by_categories,
            results=results,
        )

    return results


def _save_result(
    save_as: str,
    raw: dict[str, Any],
    *,
    metadata: dict[str, Any],
    results: dict[str, Any],
) -> None:
    results[save_as] = raw
    save_golden(save_as, raw, metadata)


def _extract_order_id(raw: dict[str, Any] | None) -> str | None:
    if not isinstance(raw, dict):
        return None
    order_obj = raw.get("order")
    if not isinstance(order_obj, dict):
        return None
    order_id = order_obj.get("order_id")
    if not isinstance(order_id, str) or not order_id:
        return None
    return order_id


async def _auth_get_with_not_found_retry(
    client: KalshiClient,
    path: str,
    *,
    attempts: int = 30,
    delay_seconds: float = 1.0,
) -> dict[str, Any] | None:
    for attempt in range(attempts):
        print(f"Recording: GET {path} (attempt {attempt + 1}/{attempts})")
        try:
            return await client._auth_get(path)
        except KalshiAPIError as exc:
            if exc.status_code != 404:
                raise
            await asyncio.sleep(delay_seconds)

    print(f"  ERROR: Not found after retries: {path}")
    return None


async def _record_portfolio_reads(client: KalshiClient, *, results: dict[str, Any]) -> None:
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


async def _record_total_resting_order_value(
    client: KalshiClient, *, results: dict[str, Any]
) -> None:
    print("Recording: GET /portfolio/summary/total_resting_order_value")
    path = "/portfolio/summary/total_resting_order_value"
    await client._rate_limiter.acquire("GET", path)
    headers = client._auth.get_headers("GET", client.API_PATH + path)
    response = await client._client.get(path, headers=headers)
    payload = response.json()

    if not isinstance(payload, dict):
        print(f"  ERROR: Unexpected response type: {type(payload)!r}")
        return

    _save_result(
        "portfolio_total_resting_order_value",
        payload,
        metadata={
            "http_status": response.status_code,
            "note": "RAW API response (SSOT); permissioned endpoint may return 403",
        },
        results=results,
    )


async def _record_single_order_fixtures(
    client: KalshiClient,
    *,
    market_ticker: str,
    safe_price: int,
    results: dict[str, Any],
) -> None:
    client_order_id = str(uuid.uuid4())
    create_raw = await _record_auth_request(
        client,
        label="POST /portfolio/orders",
        method="POST",
        path="/portfolio/orders",
        json_body={
            "ticker": market_ticker,
            "action": "buy",
            "side": "yes",
            "count": 2,
            "type": "limit",
            "yes_price": safe_price,
            "client_order_id": client_order_id,
            "post_only": True,
        },
        save_as="create_order",
        metadata={
            "ticker": market_ticker,
            "yes_price": safe_price,
            "count": 2,
            "note": "RAW API response (SSOT) - demo write fixture",
        },
        results=results,
    )

    order_id = _extract_order_id(create_raw)
    if not order_id:
        print("  ERROR: Could not extract order_id from create_order response.")
        return

    order_raw = await _auth_get_with_not_found_retry(client, f"/portfolio/orders/{order_id}")
    if order_raw is not None:
        _save_result(
            "portfolio_order_single",
            order_raw,
            metadata={"order_id": order_id, "note": "RAW API response (SSOT) - demo order lookup"},
            results=results,
        )

    queue_raw = await _auth_get_with_not_found_retry(
        client, f"/portfolio/orders/{order_id}/queue_position"
    )
    if queue_raw is not None:
        _save_result(
            "order_queue_position",
            queue_raw,
            metadata={
                "order_id": order_id,
                "note": "RAW API response (SSOT) - demo queue position",
            },
            results=results,
        )

    await _record_auth_get(
        client,
        label=f"GET /portfolio/orders/queue_positions?market_tickers={market_ticker}",
        path="/portfolio/orders/queue_positions",
        params={"market_tickers": market_ticker},
        save_as="order_queue_positions",
        metadata={
            "market_tickers": [market_ticker],
            "note": "RAW API response (SSOT) - demo queue positions",
        },
        results=results,
    )

    await _record_auth_request(
        client,
        label=f"POST /portfolio/orders/{order_id}/decrease",
        method="POST",
        path=f"/portfolio/orders/{order_id}/decrease",
        json_body={"reduce_by": 1},
        save_as="decrease_order",
        metadata={
            "order_id": order_id,
            "reduce_by": 1,
            "note": "RAW API response (SSOT) - demo decrease",
        },
        results=results,
    )

    await _record_total_resting_order_value(client, results=results)

    await _record_auth_request(
        client,
        label=f"DELETE /portfolio/orders/{order_id}",
        method="DELETE",
        path=f"/portfolio/orders/{order_id}",
        save_as="cancel_order",
        metadata={"order_id": order_id, "note": "RAW API response (SSOT) - demo cancel"},
        results=results,
    )


async def _record_amend_order_fixture(
    client: KalshiClient,
    *,
    market_ticker: str,
    safe_price: int,
    yes_ask: int,
    results: dict[str, Any],
) -> None:
    amend_client_order_id = str(uuid.uuid4())
    print("Recording: POST /portfolio/orders (for amend)")

    try:
        create_raw = await _auth_request_raw(
            client,
            method="POST",
            path="/portfolio/orders",
            json_body={
                "ticker": market_ticker,
                "action": "buy",
                "side": "yes",
                "count": 1,
                "type": "limit",
                "yes_price": safe_price,
                "client_order_id": amend_client_order_id,
                "post_only": True,
            },
        )
    except Exception as exc:
        print(f"  ERROR: {exc}")
        return

    amend_order_id = _extract_order_id(create_raw)
    if not amend_order_id:
        print("  ERROR: Could not extract order_id for amend fixture.")
        return

    updated_client_order_id = str(uuid.uuid4())
    new_price = max(1, min(safe_price + 1, yes_ask - 1))
    if new_price == safe_price:
        new_price = max(1, safe_price - 1)

    amend_raw = await _record_auth_request(
        client,
        label=f"POST /portfolio/orders/{amend_order_id}/amend",
        method="POST",
        path=f"/portfolio/orders/{amend_order_id}/amend",
        json_body={
            "ticker": market_ticker,
            "side": "yes",
            "action": "buy",
            "client_order_id": amend_client_order_id,
            "updated_client_order_id": updated_client_order_id,
            "yes_price": new_price,
        },
        save_as="amend_order",
        metadata={
            "order_id": amend_order_id,
            "ticker": market_ticker,
            "yes_price": new_price,
            "note": "RAW API response (SSOT) - demo amend",
        },
        results=results,
    )

    cancel_target_id = amend_order_id
    cancel_order_id = _extract_order_id(amend_raw)
    if cancel_order_id:
        cancel_target_id = cancel_order_id

    print(f"Recording: DELETE /portfolio/orders/{cancel_target_id} (post-amend cleanup)")
    try:
        await _auth_request_raw(
            client, method="DELETE", path=f"/portfolio/orders/{cancel_target_id}"
        )
    except Exception as exc:
        print(f"  ERROR: {exc}")


async def _record_batch_order_fixtures(
    client: KalshiClient,
    *,
    market_ticker: str,
    safe_price: int,
    results: dict[str, Any],
) -> None:
    batch_orders = [
        {
            "ticker": market_ticker,
            "action": "buy",
            "side": "yes",
            "count": 1,
            "type": "limit",
            "yes_price": safe_price,
            "client_order_id": str(uuid.uuid4()),
            "post_only": True,
        },
        {
            "ticker": market_ticker,
            "action": "buy",
            "side": "yes",
            "count": 1,
            "type": "limit",
            "yes_price": safe_price,
            "client_order_id": str(uuid.uuid4()),
            "post_only": True,
        },
    ]

    batch_create_raw = await _record_auth_request(
        client,
        label="POST /portfolio/orders/batched",
        method="POST",
        path="/portfolio/orders/batched",
        json_body={"orders": batch_orders},
        batch_size=len(batch_orders),
        save_as="batch_create_orders",
        metadata={
            "ticker": market_ticker,
            "orders": len(batch_orders),
            "note": "RAW API response (SSOT)",
        },
        results=results,
    )

    batch_order_ids: list[str] = []
    if isinstance(batch_create_raw, dict):
        orders_obj = batch_create_raw.get("orders")
        if isinstance(orders_obj, list):
            for item in orders_obj:
                if not isinstance(item, dict):
                    continue
                order_obj = item.get("order")
                if not isinstance(order_obj, dict):
                    continue
                oid = order_obj.get("order_id")
                if isinstance(oid, str) and oid:
                    batch_order_ids.append(oid)

    if not batch_order_ids:
        print("  ERROR: Unable to extract order IDs from batch create response.")
        return

    await _record_auth_request(
        client,
        label="DELETE /portfolio/orders/batched",
        method="DELETE",
        path="/portfolio/orders/batched",
        json_body={"ids": batch_order_ids},
        batch_size=len(batch_order_ids),
        save_as="batch_cancel_orders",
        metadata={"orders": len(batch_order_ids), "note": "RAW API response (SSOT)"},
        results=results,
    )


async def _record_order_write_fixtures(client: KalshiClient, *, results: dict[str, Any]) -> None:
    print("\n=== ORDER WRITE ENDPOINTS (DEMO ONLY) ===\n")
    raw_markets = await client._get("/markets", {"status": "open", "limit": 50})
    market_pick = _select_market_for_order_writes(raw_markets)
    if not market_pick:
        print("  ERROR: Unable to find an active market suitable for order write fixtures.")
        return

    market_ticker, safe_price, yes_ask = market_pick
    print(f"  Using market: {market_ticker} (yes_ask={yes_ask}, safe_price={safe_price})")

    await _record_single_order_fixtures(
        client, market_ticker=market_ticker, safe_price=safe_price, results=results
    )
    await _record_amend_order_fixture(
        client,
        market_ticker=market_ticker,
        safe_price=safe_price,
        yes_ask=yes_ask,
        results=results,
    )
    await _record_batch_order_fixtures(
        client, market_ticker=market_ticker, safe_price=safe_price, results=results
    )


async def record_authenticated_endpoints(
    *, include_writes: bool, record_portfolio_reads: bool
) -> dict[str, Any]:
    """Record responses from authenticated endpoints (portfolio, orders)."""
    config = get_config()
    results: dict[str, Any] = {}

    key_id, private_key_path, private_key_b64 = resolve_kalshi_auth_env(
        environment=config.environment
    )
    key_id_var, private_key_path_var, private_key_b64_var = get_kalshi_auth_env_var_names(
        environment=config.environment
    )

    if not key_id:
        print("\n=== AUTHENTICATED ENDPOINTS ===\n")
        print(f"  SKIPPED: No {key_id_var} configured")
        if key_id_var != "KALSHI_KEY_ID":
            print("           (Fallback also supports KALSHI_KEY_ID)")
        return results

    if not private_key_path and not private_key_b64:
        print("\n=== AUTHENTICATED ENDPOINTS ===\n")
        print(f"  SKIPPED: No {private_key_path_var} configured")
        print(f"           (or {private_key_b64_var})")
        if private_key_path_var != "KALSHI_PRIVATE_KEY_PATH":
            print(
                "           (Fallback also supports KALSHI_PRIVATE_KEY_PATH / "
                "KALSHI_PRIVATE_KEY_B64)"
            )
        return results

    try:
        async with KalshiClient(
            key_id=key_id,
            private_key_path=private_key_path,
            private_key_b64=private_key_b64,
            environment=config.environment.value,
        ) as client:
            if record_portfolio_reads:
                await _record_portfolio_reads(client, results=results)

            if include_writes:
                if config.environment != Environment.DEMO:
                    print("\n=== ORDER WRITE ENDPOINTS ===\n")
                    print("  SKIPPED: Order write fixtures are demo-only (use --env demo).")
                else:
                    await _record_order_write_fixtures(client, results=results)

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
        choices=["public", "authenticated", "order_ops", "all"],
        default="all",
        help="Which endpoints to record",
    )
    parser.add_argument(
        "--include-writes",
        action="store_true",
        help="Also record order write fixtures (demo only).",
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
    try:
        set_environment(Environment(env))
    except ValueError:
        print(f"Invalid KALSHI_ENVIRONMENT: {env!r} (expected 'prod' or 'demo')")
        return

    print(f"\n{'=' * 60}")
    print(f"RECORDING API RESPONSES FROM: {env.upper()}")
    print(f"{'=' * 60}")

    wants_writes = args.include_writes or args.endpoint == "order_ops"

    if wants_writes and env != "demo":
        print("\nERROR: Refusing to record order write fixtures outside demo.")
        print("Re-run with: --env demo --include-writes")
        return

    if env == "prod":
        print("\nWARNING: Using PRODUCTION API")
        print("Recording is read-only, but be aware this hits the real API.")
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
        all_results["authenticated"] = await record_authenticated_endpoints(
            include_writes=args.include_writes, record_portfolio_reads=True
        )

    if args.endpoint == "order_ops":
        all_results["order_ops"] = await record_authenticated_endpoints(
            include_writes=True, record_portfolio_reads=False
        )

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
