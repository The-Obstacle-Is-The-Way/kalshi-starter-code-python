from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kalshi_research.exa.models.answer import AnswerResponse
from kalshi_research.exa.models.contents import ContentsResponse
from kalshi_research.exa.models.search import SearchResponse
from kalshi_research.exa.models.similar import FindSimilarResponse


def _load_exa_fixture(name: str) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    fixture_path = root / "tests" / "fixtures" / "golden" / "exa" / name
    data = json.loads(fixture_path.read_text())
    return data["response"]


def test_exa_search_fixture_matches_model() -> None:
    SearchResponse.model_validate(_load_exa_fixture("search_response.json"))


def test_exa_search_and_contents_fixture_matches_model() -> None:
    SearchResponse.model_validate(_load_exa_fixture("search_and_contents_response.json"))


def test_exa_contents_fixture_matches_model() -> None:
    ContentsResponse.model_validate(_load_exa_fixture("get_contents_response.json"))


def test_exa_find_similar_fixture_matches_model() -> None:
    FindSimilarResponse.model_validate(_load_exa_fixture("find_similar_response.json"))


def test_exa_answer_fixture_matches_model() -> None:
    AnswerResponse.model_validate(_load_exa_fixture("answer_response.json"))
