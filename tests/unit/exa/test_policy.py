from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from kalshi_research.exa.cache import ExaCache
from kalshi_research.exa.policy import ExaBudget, ExaMode, ExaPolicy, extract_exa_cost_total

if TYPE_CHECKING:
    from pathlib import Path


def test_policy_mode_maps_to_exa_search_type() -> None:
    assert ExaPolicy.from_mode(mode=ExaMode.FAST).exa_search_type == "fast"
    assert ExaPolicy.from_mode(mode=ExaMode.STANDARD).exa_search_type == "auto"
    assert ExaPolicy.from_mode(mode=ExaMode.DEEP).exa_search_type == "deep"


def test_policy_mode_controls_default_answer_and_text_inclusion() -> None:
    assert ExaPolicy.from_mode(mode=ExaMode.FAST).include_answer is False
    assert ExaPolicy.from_mode(mode=ExaMode.FAST).include_full_text is False

    assert ExaPolicy.from_mode(mode=ExaMode.STANDARD).include_answer is True
    assert ExaPolicy.from_mode(mode=ExaMode.STANDARD).include_full_text is True

    assert ExaPolicy.from_mode(mode=ExaMode.DEEP).include_answer is True
    assert ExaPolicy.from_mode(mode=ExaMode.DEEP).include_full_text is True


def test_budget_enforces_limit_before_spending() -> None:
    budget = ExaBudget(limit_usd=0.10)
    assert budget.can_spend(0.03) is True

    budget.record_spend(0.03)
    assert budget.spent_usd == pytest.approx(0.03)
    assert budget.remaining_usd == pytest.approx(0.07)

    assert budget.can_spend(0.08) is False
    assert budget.can_spend(0.07) is True


def test_budget_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="limit_usd must be positive"):
        ExaBudget(limit_usd=0.0)

    with pytest.raises(ValueError, match="spent_usd must be non-negative"):
        ExaBudget(limit_usd=1.0, spent_usd=-0.01)

    budget = ExaBudget(limit_usd=1.0)
    with pytest.raises(ValueError, match="estimated_usd must be non-negative"):
        budget.can_spend(-0.01)

    with pytest.raises(ValueError, match="actual_usd must be non-negative"):
        budget.record_spend(-0.01)


def test_cache_params_are_stable_and_mode_scoped(tmp_path: Path) -> None:
    cache = ExaCache(tmp_path)

    policy_standard = ExaPolicy.from_mode(mode=ExaMode.STANDARD)
    params_a = {
        "query": "prediction markets",
        "exclude_domains": ["b.com", "a.com"],
        "budget_usd": 999.0,
    }
    cache.set("search", policy_standard.normalize_cache_params(params_a), {"ok": True})

    params_b = {
        "query": "prediction markets",
        "exclude_domains": ["a.com", "b.com"],
    }
    assert cache.get("search", policy_standard.normalize_cache_params(params_b)) == {"ok": True}

    policy_fast = ExaPolicy.from_mode(mode=ExaMode.FAST)
    assert cache.get("search", policy_fast.normalize_cache_params(params_b)) is None


def test_policy_from_mode_rejects_non_positive_budget() -> None:
    with pytest.raises(ValueError, match="budget_usd must be positive"):
        ExaPolicy.from_mode(mode=ExaMode.STANDARD, budget_usd=0.0)

    with pytest.raises(ValueError, match="budget_usd must be positive"):
        ExaPolicy.from_mode(mode=ExaMode.STANDARD, budget_usd=-0.01)


def test_estimate_search_cost_usd_returns_zero_when_num_results_is_non_positive() -> None:
    policy = ExaPolicy.from_mode(mode=ExaMode.STANDARD)
    assert (
        policy.estimate_search_cost_usd(
            num_results=0,
            include_text=True,
            include_highlights=True,
        )
        == 0.0
    )
    assert (
        policy.estimate_search_cost_usd(
            num_results=-1,
            include_text=True,
            include_highlights=True,
        )
        == 0.0
    )


def test_estimate_search_cost_usd_covers_tiers_and_output_options() -> None:
    fast = ExaPolicy.from_mode(mode=ExaMode.FAST)
    deep = ExaPolicy.from_mode(mode=ExaMode.DEEP)

    assert fast.estimate_search_cost_usd(
        num_results=25,
        include_text=False,
        include_highlights=False,
    ) == pytest.approx(0.006)
    assert fast.estimate_search_cost_usd(
        num_results=100,
        include_text=False,
        include_highlights=False,
    ) == pytest.approx(0.03)
    assert deep.estimate_search_cost_usd(
        num_results=25,
        include_text=False,
        include_highlights=False,
    ) == pytest.approx(0.018)

    cost_with_text_and_highlights = fast.estimate_search_cost_usd(
        num_results=10,
        include_text=True,
        include_highlights=True,
    )
    assert cost_with_text_and_highlights > 0.006


def test_estimate_answer_cost_usd_is_conservative() -> None:
    policy = ExaPolicy.from_mode(mode=ExaMode.STANDARD)
    assert policy.estimate_answer_cost_usd(include_text=True) == 0.05
    assert policy.estimate_answer_cost_usd(include_text=False) == 0.03


def test_extract_exa_cost_total_handles_missing_values() -> None:
    assert extract_exa_cost_total(object()) == 0.0
    assert extract_exa_cost_total(SimpleNamespace(cost_dollars=None)) == 0.0
    assert extract_exa_cost_total(SimpleNamespace(cost_dollars=SimpleNamespace(total=None))) == 0.0
    assert extract_exa_cost_total(
        SimpleNamespace(cost_dollars=SimpleNamespace(total=0.12))
    ) == pytest.approx(0.12)
