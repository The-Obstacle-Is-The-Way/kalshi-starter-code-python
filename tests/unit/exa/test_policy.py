from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from kalshi_research.exa.cache import ExaCache
from kalshi_research.exa.policy import ExaBudget, ExaMode, ExaPolicy

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
