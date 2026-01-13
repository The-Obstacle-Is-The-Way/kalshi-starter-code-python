from __future__ import annotations

from kalshi_research.exa.models.answer import AnswerResponse
from kalshi_research.exa.models.contents import ContentsResponse
from kalshi_research.exa.models.research import ResearchTask, ResearchTaskListResponse
from kalshi_research.exa.models.search import SearchResponse
from kalshi_research.exa.models.similar import FindSimilarResponse
from tests.golden_fixtures import load_golden_response


def test_exa_search_fixture_matches_model() -> None:
    SearchResponse.model_validate(load_golden_response("exa", "search_response.json"))


def test_exa_search_and_contents_fixture_matches_model() -> None:
    SearchResponse.model_validate(load_golden_response("exa", "search_and_contents_response.json"))


def test_exa_search_empty_published_date_fixture_matches_model() -> None:
    SearchResponse.model_validate(
        load_golden_response("exa", "search_empty_published_date_response.json")
    )


def test_exa_contents_fixture_matches_model() -> None:
    ContentsResponse.model_validate(load_golden_response("exa", "get_contents_response.json"))


def test_exa_find_similar_fixture_matches_model() -> None:
    FindSimilarResponse.model_validate(load_golden_response("exa", "find_similar_response.json"))


def test_exa_answer_fixture_matches_model() -> None:
    AnswerResponse.model_validate(load_golden_response("exa", "answer_response.json"))


def test_exa_research_task_create_fixture_matches_model() -> None:
    ResearchTask.model_validate(load_golden_response("exa", "research_task_create_response.json"))


def test_exa_research_task_fixture_matches_model() -> None:
    ResearchTask.model_validate(load_golden_response("exa", "research_task_response.json"))


def test_exa_research_task_list_fixture_matches_model() -> None:
    ResearchTaskListResponse.model_validate(
        load_golden_response("exa", "research_task_list_response.json")
    )
