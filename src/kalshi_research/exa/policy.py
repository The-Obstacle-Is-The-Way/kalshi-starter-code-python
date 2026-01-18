"""Exa endpoint selection policy and budget enforcement utilities.

This module is intentionally lightweight: it is used by CLI-facing research flows to:
- pick deterministic Exa parameters/endpoints based on a user-selected mode, and
- enforce a per-command USD budget before making new API calls.

It is *not* an agent system or a production service policy layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExaMode(str, Enum):
    """Cost/quality preset for Exa-powered research."""

    FAST = "fast"
    STANDARD = "standard"
    DEEP = "deep"


DEFAULT_BUDGET_USD_BY_MODE: dict[ExaMode, float] = {
    ExaMode.FAST: 0.05,
    ExaMode.STANDARD: 0.25,
    ExaMode.DEEP: 1.00,
}


@dataclass(frozen=True)
class ExaPolicy:
    """Deterministic configuration for Exa endpoint usage."""

    mode: ExaMode
    budget_usd: float

    @classmethod
    def from_mode(
        cls, *, mode: ExaMode = ExaMode.STANDARD, budget_usd: float | None = None
    ) -> ExaPolicy:
        """Create a policy using the mode's default budget when not specified."""
        resolved_budget = DEFAULT_BUDGET_USD_BY_MODE[mode] if budget_usd is None else budget_usd
        if resolved_budget <= 0:
            raise ValueError("budget_usd must be positive")
        return cls(mode=mode, budget_usd=resolved_budget)

    @property
    def exa_search_type(self) -> str:
        """Return the Exa `/search` `type` value for this policy.

        This is distinct from the Exa endpoint selection (/search vs /answer vs /research).
        """
        if self.mode == ExaMode.FAST:
            return "fast"
        if self.mode == ExaMode.DEEP:
            return "deep"
        return "auto"

    @property
    def include_full_text(self) -> bool:
        """Whether search results should include full page text by default."""
        return self.mode != ExaMode.FAST

    @property
    def include_answer(self) -> bool:
        """Whether a topic-summary `answer` call is allowed by default."""
        return self.mode != ExaMode.FAST

    def estimate_search_cost_usd(
        self,
        *,
        num_results: int,
        include_text: bool,
        include_highlights: bool,
        search_type: str | None = None,
    ) -> float:
        """Estimate an upper-bound cost for a `/search` request.

        This is a conservative estimate derived from Exa pricing tables embedded in
        `docs/_vendor-docs/exa-api-reference.md`. It exists to avoid kicking off new
        API calls that would exceed a user-specified budget.
        """
        if num_results <= 0:
            return 0.0

        effective_type = search_type or self.exa_search_type
        base_cost = 0.015 if effective_type == "deep" else 0.005

        per_page_cost = 0.0
        if include_text:
            per_page_cost += 0.001
        if include_highlights:
            per_page_cost += 0.001

        # Multiply by a small safety factor to reduce the chance of overruns if Exa pricing
        # drifts slightly or the "auto" type chooses a more expensive backend.
        safety_factor = 1.2
        return (base_cost + (float(num_results) * per_page_cost)) * safety_factor

    def estimate_answer_cost_usd(self, *, include_text: bool) -> float:
        """Estimate a conservative cost for an `/answer` request.

        Exa does not expose a simple static price table for `answer` in the same way as search.
        We use a conservative constant to keep budgets meaningful.
        """
        # Text answers with citations are the common case in this repo.
        return 0.05 if include_text else 0.03

    def normalize_cache_params(self, params: dict[str, object]) -> dict[str, object]:
        """Return a stable cache params mapping for ExaCache keys.

        - Adds `exa_policy_mode` so different modes do not collide in cache.
        - Sorts list-like domain filters to make the cache key order-insensitive.
        - Excludes budget fields (budget should not invalidate cache entries).
        """
        normalized: dict[str, object] = {**params, "exa_policy_mode": self.mode.value}

        for key in ("include_domains", "exclude_domains"):
            value = normalized.get(key)
            if isinstance(value, list) and all(isinstance(item, str) for item in value):
                normalized[key] = sorted(value)

        normalized.pop("budget_usd", None)
        return normalized


@dataclass
class ExaBudget:
    """Mutable budget tracker for a single CLI command invocation."""

    limit_usd: float
    spent_usd: float = 0.0

    def __post_init__(self) -> None:
        if self.limit_usd <= 0:
            raise ValueError("limit_usd must be positive")
        if self.spent_usd < 0:
            raise ValueError("spent_usd must be non-negative")

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.limit_usd - self.spent_usd)

    def can_spend(self, estimated_usd: float) -> bool:
        if estimated_usd < 0:
            raise ValueError("estimated_usd must be non-negative")
        return (self.spent_usd + estimated_usd) <= self.limit_usd

    def record_spend(self, actual_usd: float) -> None:
        if actual_usd < 0:
            raise ValueError("actual_usd must be non-negative")
        self.spent_usd += actual_usd


def extract_exa_cost_total(response: object) -> float:
    """Best-effort extraction of `cost_dollars.total` from an Exa response model."""
    cost = getattr(response, "cost_dollars", None)
    if cost is None:
        return 0.0
    total = getattr(cost, "total", None)
    return float(total) if total is not None else 0.0
