#!/usr/bin/env python3
"""
Record actual API responses from Exa API as golden fixtures.

These fixtures become the SSOT for what Exa returns (schema + wrapper keys),
reducing the risk that unit tests diverge from reality.

Usage:
    # Record core endpoints (requires EXA_API_KEY)
    uv run python scripts/record_exa_responses.py

    # Record only /research/v1 fixtures (higher cost/latency)
    uv run python scripts/record_exa_responses.py --only-research

    # Include /research/v1 (higher cost/latency)
    uv run python scripts/record_exa_responses.py --include-research

Note:
    All operations are READ-ONLY.
    Exa responses are not expected to contain account identifiers, but fixtures still
    include a `_metadata` block for provenance.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from dotenv import load_dotenv

from kalshi_research.exa.client import ExaClient
from kalshi_research.exa.models.answer import AnswerRequest
from kalshi_research.exa.models.common import (
    ContentsRequest,
    HighlightsOptions,
    TextContentsOptions,
)
from kalshi_research.exa.models.contents import GetContentsRequest
from kalshi_research.exa.models.research import ResearchRequest
from kalshi_research.exa.models.search import SearchRequest
from kalshi_research.exa.models.similar import FindSimilarRequest

load_dotenv()

GOLDEN_EXA_DIR: Final[Path] = (
    Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "golden" / "exa"
)


def _now_utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def save_golden(
    *,
    name: str,
    response: dict[str, Any],
    metadata: dict[str, Any],
) -> Path:
    GOLDEN_EXA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = GOLDEN_EXA_DIR / f"{name}_response.json"
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


async def _record_post(
    *,
    exa: ExaClient,
    name: str,
    endpoint: str,
    json_body: dict[str, Any],
    metadata: dict[str, Any],
) -> None:
    print(f"Recording: POST {endpoint} -> {name}_response.json")
    raw = await exa._request("POST", endpoint, json_body=json_body)
    save_golden(name=name, response=raw, metadata={"endpoint": endpoint, **metadata})


async def _record_get(
    *,
    exa: ExaClient,
    name: str,
    endpoint: str,
    params: dict[str, Any] | None = None,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    print(f"Recording: GET {endpoint} -> {name}_response.json")
    raw = await exa._request("GET", endpoint, params=params)
    save_golden(name=name, response=raw, metadata={"endpoint": endpoint, **metadata})
    return raw


async def _record_core_endpoints(*, exa: ExaClient) -> None:
    query = "Example Domain"
    stable_domain = "example.com"
    example_url = "https://example.com"

    # 1) /search (no contents)
    search_request = SearchRequest(query=query, num_results=1, include_domains=[stable_domain])
    await _record_post(
        exa=exa,
        name="search",
        endpoint="/search",
        json_body=search_request.model_dump(by_alias=True, exclude_none=True, mode="json"),
        metadata={"query": query, "num_results": 1, "include_domains": [stable_domain]},
    )

    # 2) /search (with contents)
    contents = ContentsRequest(
        text=TextContentsOptions(max_characters=500),
        highlights=HighlightsOptions(query=query, num_sentences=2, highlights_per_url=1),
    )
    search_contents_request = SearchRequest(
        query=query,
        num_results=1,
        include_domains=[stable_domain],
        contents=contents,
    )
    await _record_post(
        exa=exa,
        name="search_and_contents",
        endpoint="/search",
        json_body=search_contents_request.model_dump(by_alias=True, exclude_none=True, mode="json"),
        metadata={
            "query": query,
            "num_results": 1,
            "include_domains": [stable_domain],
            "note": "Recorded via /search with a contents object",
        },
    )

    # 3) /contents
    contents_request = GetContentsRequest(
        urls=[example_url],
        text=TextContentsOptions(max_characters=800),
    )
    await _record_post(
        exa=exa,
        name="get_contents",
        endpoint="/contents",
        json_body=contents_request.model_dump(by_alias=True, exclude_none=True, mode="json"),
        metadata={"urls": [example_url]},
    )

    # 4) /findSimilar
    find_similar_request = FindSimilarRequest(url=example_url, num_results=3)
    find_similar_payload = find_similar_request.model_dump(
        by_alias=True, exclude_none=True, mode="json"
    )
    await _record_post(
        exa=exa,
        name="find_similar",
        endpoint="/findSimilar",
        json_body=find_similar_payload,
        metadata={"url": example_url, "num_results": 3},
    )

    # 5) /answer
    answer_query = "What is Example Domain?"
    answer_request = AnswerRequest(query=answer_query, text=False)
    await _record_post(
        exa=exa,
        name="answer",
        endpoint="/answer",
        json_body=answer_request.model_dump(by_alias=True, exclude_none=True, mode="json"),
        metadata={"query": answer_query},
    )


def _is_safe_research_task_list_response(*, response: dict[str, Any], research_id: str) -> bool:
    data = response.get("data")
    if not isinstance(data, list):
        return False
    if not data:
        return True
    if not isinstance(data[0], dict):
        return False
    return data[0].get("researchId") == research_id


async def _record_research_endpoints(*, exa: ExaClient) -> None:
    # NOTE: /research/v1 can be higher cost/latency. Keep the task small.
    instructions = "Summarize https://example.com in 1 short sentence."
    research_request = ResearchRequest(instructions=instructions)

    print("Recording: POST /research/v1 -> research_task_create_response.json")
    created = await exa._request(
        "POST",
        "/research/v1",
        json_body=research_request.model_dump(by_alias=True, exclude_none=True, mode="json"),
    )
    save_golden(
        name="research_task_create",
        response=created,
        metadata={"endpoint": "/research/v1", "instructions": instructions},
    )

    research_id = created.get("researchId")
    if not isinstance(research_id, str) or not research_id:
        raise RuntimeError("Unexpected /research/v1 create response: missing researchId")

    # 0) /research/v1 (list) - keep limit=1 to avoid capturing unrelated tasks/instructions.
    list_limit = 1
    print("Recording: GET /research/v1 (list) -> research_task_list_response.json")
    list_response = await exa._request("GET", "/research/v1", params={"limit": list_limit})
    if not _is_safe_research_task_list_response(response=list_response, research_id=research_id):
        raise RuntimeError(
            "Refusing to record research task list fixture: "
            "response did not include the created task."
        )
    save_golden(
        name="research_task_list",
        response=list_response,
        metadata={
            "endpoint": "/research/v1",
            "limit": list_limit,
            "note": "Recorded after creating example.com task; limit=1 avoids unrelated tasks.",
        },
    )

    print("Polling: GET /research/v1/{researchId} until terminal status...")
    deadline = time.monotonic() + 180.0
    while True:
        task = await exa._request("GET", f"/research/v1/{research_id}")
        status = task.get("status")
        if status in ("completed", "failed", "canceled"):
            save_golden(
                name="research_task",
                response=task,
                metadata={
                    "endpoint": f"/research/v1/{research_id}",
                    "note": "Terminal response",
                },
            )
            return
        if time.monotonic() >= deadline:
            raise TimeoutError("Research task did not reach a terminal status in time")
        await asyncio.sleep(5.0)


def _write_exa_recording_summary(*, include_research: bool) -> None:
    summary_path = GOLDEN_EXA_DIR / "_recording_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "_metadata": {
                    "recorded_at": _now_utc_iso(),
                    "endpoint": "_recording_summary",
                    "environment": "prod",
                },
                "response": {
                    "endpoints_recorded": sorted(
                        [p.name for p in GOLDEN_EXA_DIR.glob("*_response.json")]
                    ),
                    "include_research": include_research,
                },
            },
            indent=2,
        )
    )
    print(f"\nSaved Exa summary: {summary_path}")


async def record_exa_fixtures(*, include_research: bool, only_research: bool) -> None:
    if not os.getenv("EXA_API_KEY"):
        raise RuntimeError("EXA_API_KEY not configured (check .env)")

    async with ExaClient.from_env() as exa:
        if not only_research:
            await _record_core_endpoints(exa=exa)
        if include_research:
            await _record_research_endpoints(exa=exa)

    _write_exa_recording_summary(include_research=include_research)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Record Exa API responses as golden fixtures")
    parser.add_argument(
        "--only-research",
        action="store_true",
        help="Record only /research/v1 fixtures (avoid re-recording core endpoints).",
    )
    parser.add_argument(
        "--include-research",
        action="store_true",
        help="Also record /research/v1 fixtures (higher cost/latency).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Run non-interactively (required if stdin is not a TTY).",
    )
    args = parser.parse_args()

    if not args.yes and not sys.stdin.isatty():
        print("Refusing to record in non-interactive mode without --yes.")
        return

    include_research = args.include_research or args.only_research

    print(f"\n{'=' * 60}")
    print("RECORDING EXA API RESPONSES")
    print(f"{'=' * 60}\n")
    await record_exa_fixtures(include_research=include_research, only_research=args.only_research)

    print(f"\n{'=' * 60}")
    print(f"DONE! Exa golden fixtures saved to: {GOLDEN_EXA_DIR}")
    print(f"{'=' * 60}\n")

    print("Files created:")
    for f in sorted(GOLDEN_EXA_DIR.glob("*.json")):
        print(f"  {f.name}")


if __name__ == "__main__":
    asyncio.run(main())
