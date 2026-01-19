#!/usr/bin/env python3
"""
Record actual API responses from Exa Websets API as golden fixtures.

These fixtures become the SSOT for what Exa Websets returns (schema + wrapper keys),
reducing the risk that unit tests diverge from reality.

Usage:
    # Record Websets fixtures (requires EXA_API_KEY and --yes flag)
    uv run python scripts/record_exa_websets_responses.py --yes

Note:
    This script makes real Exa Websets API calls and may incur cost.

    - Websets operations involve creating resources (not read-only).
    - Resources are canceled/cleaned up after recording to minimize cost.
    - The --yes flag is required to confirm you understand cost implications.

    Fixtures include a `_metadata` block for provenance.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from dotenv import load_dotenv

from kalshi_research.exa.websets.client import ExaWebsetsClient
from kalshi_research.exa.websets.models import (
    CreateWebsetParameters,
    CreateWebsetSearchParameters,
    PreviewWebsetParameters,
)

load_dotenv()

GOLDEN_WEBSETS_DIR: Final[Path] = (
    Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "golden" / "exa_websets"
)


def _now_utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def save_golden(
    *,
    name: str,
    response: dict[str, Any],
    metadata: dict[str, Any],
) -> Path:
    """Save a golden fixture to disk with metadata."""
    GOLDEN_WEBSETS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = GOLDEN_WEBSETS_DIR / f"{name}_response.json"
    output: dict[str, Any] = {
        "_metadata": {
            "recorded_at": _now_utc_iso(),
            "endpoint": metadata.get("endpoint"),
            "environment": "prod",
            "sanitized": False,
            **metadata,
        },
        "response": response,
    }
    filepath.write_text(json.dumps(output, indent=2, default=str))
    print(f"  Saved: {filepath}")
    return filepath


async def record_websets_fixtures() -> None:
    """Record Websets API responses as golden fixtures."""
    print("Recording Exa Websets API responses...")
    print("=" * 60)

    async with ExaWebsetsClient.from_env() as client:
        # 1. Preview a Webset search (no resource created)
        print("\n[1/6] Recording: POST /v0/websets/preview")
        preview_params = PreviewWebsetParameters(
            search=CreateWebsetSearchParameters(
                query="Tech startups in San Francisco founded in 2024",
                count=5,
            )
        )
        preview_response = await client.preview_webset(preview_params)
        save_golden(
            name="preview_webset",
            response=preview_response.model_dump(by_alias=True, mode="json"),
            metadata={"endpoint": "POST /v0/websets/preview"},
        )

        # 2. Create a Webset
        print("\n[2/6] Recording: POST /v0/websets")
        create_params = CreateWebsetParameters(
            search=CreateWebsetSearchParameters(
                query="SSOT fixture test - AI research labs in Europe",
                count=3,
            ),
            title="SSOT Fixture Test Webset",
            external_id=f"ssot-fixture-test-{int(datetime.now(UTC).timestamp())}",
        )
        webset = await client.create_webset(create_params)
        webset_id = webset.id
        save_golden(
            name="create_webset",
            response=webset.model_dump(by_alias=True, mode="json"),
            metadata={"endpoint": "POST /v0/websets", "webset_id": webset_id},
        )

        # 3. Get the created Webset
        print("\n[3/6] Recording: GET /v0/websets/{id}")
        get_response = await client.get_webset(webset_id)
        save_golden(
            name="get_webset",
            response=get_response.model_dump(by_alias=True, mode="json"),
            metadata={"endpoint": f"GET /v0/websets/{webset_id}", "webset_id": webset_id},
        )

        # 4. List Webset items (may be empty if search hasn't completed)
        print("\n[4/6] Recording: GET /v0/websets/{webset}/items")
        items_response = await client.list_webset_items(webset_id, limit=10)
        save_golden(
            name="list_webset_items",
            response=items_response.model_dump(by_alias=True, mode="json"),
            metadata={
                "endpoint": f"GET /v0/websets/{webset_id}/items",
                "webset_id": webset_id,
            },
        )

        # 5. Get search from the Webset (initial search created with Webset)
        if webset.searches:
            search_id = webset.searches[0].id
            print(f"\n[5/6] Recording: GET /v0/websets/{webset_id}/searches/{search_id}")
            search_response = await client.get_webset_search(webset_id, search_id)
            save_golden(
                name="get_webset_search",
                response=search_response.model_dump(by_alias=True, mode="json"),
                metadata={
                    "endpoint": f"GET /v0/websets/{webset_id}/searches/{search_id}",
                    "webset_id": webset_id,
                    "search_id": search_id,
                },
            )
        else:
            print("\n[5/6] SKIPPED: No searches in Webset")

        # 6. Cancel the Webset (cleanup)
        print(f"\n[6/6] Recording: POST /v0/websets/{webset_id}/cancel")
        cancel_response = await client.cancel_webset(webset_id)
        save_golden(
            name="cancel_webset",
            response=cancel_response.model_dump(by_alias=True, mode="json"),
            metadata={
                "endpoint": f"POST /v0/websets/{webset_id}/cancel",
                "webset_id": webset_id,
            },
        )

        print("\n" + "=" * 60)
        print("✓ Recording complete!")
        print(f"  Fixtures saved to: {GOLDEN_WEBSETS_DIR}")

    # Save recording summary
    summary = {
        "recorded_at": _now_utc_iso(),
        "fixtures": [
            "preview_webset_response.json",
            "create_webset_response.json",
            "get_webset_response.json",
            "list_webset_items_response.json",
            "get_webset_search_response.json",
            "cancel_webset_response.json",
        ],
        "api_version": "v0",
        "note": "Webset was canceled after recording to minimize cost",
    }
    summary_path = GOLDEN_WEBSETS_DIR / "_recording_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"  Summary: {summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Record Exa Websets API responses as golden fixtures"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm you understand this will make real API calls and may incur cost",
    )
    args = parser.parse_args()

    if not args.yes:
        print("ERROR: This script makes real API calls and may incur cost.")
        print("       Run with --yes to confirm you understand this.")
        print()
        print("Usage: uv run python scripts/record_exa_websets_responses.py --yes")
        sys.exit(1)

    try:
        asyncio.run(record_websets_fixtures())
    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nNote: If EXA_API_KEY is not set, export it first:")
        print("  export EXA_API_KEY=your_key_here")
        sys.exit(1)


if __name__ == "__main__":
    main()
