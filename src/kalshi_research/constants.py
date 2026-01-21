"""Centralized policy constants for the Kalshi Research platform.

This module defines named constants for policy-encoding literals that were previously
scattered across the codebase. Centralizing these values:

- Prevents subtle divergence bugs when the same concept is used in multiple places
- Makes policy decisions easy to audit and modify
- Follows Clean Code standards (named constants over magic numbers)

See DEBT-047 for rationale and migration status.
"""

from __future__ import annotations

# =============================================================================
# Pagination & Fetch Limits
# =============================================================================

# Default page size for paginated API requests (events, markets, trades).
#
# Used by:
# - data/fetcher.py: event sync
# - cli/scan.py: opportunity scanning
# - cli/market.py: market listing
#
# The Kalshi API supports up to 1000 per page, but 200 is a reasonable default
# that balances throughput with memory usage and rate limiting.
DEFAULT_PAGINATION_LIMIT: int = 200

# =============================================================================
# Orderbook
# =============================================================================

# Default depth (number of price levels) for orderbook fetches.
#
# Used by:
# - api/client.py: get_orderbook()
# - cli/market.py: orderbook display
# - analysis/liquidity.py: liquidity calculations
#
# Kalshi's default is 10; this matches the API default while making
# the policy explicit and auditable.
DEFAULT_ORDERBOOK_DEPTH: int = 10

# =============================================================================
# Scanner Thresholds
# =============================================================================

# Probability range for close-race detection.
#
# Markets with a midpoint probability in this range are considered "close races"
# - uncertain enough to warrant research for potential edge.
#
# Used by:
# - analysis/scanner.py: MarketScanner.scan_close_races()
# - cli/scan.py: opportunities --filter close-race
#
# Default (0.40, 0.60) means 40%-60% probability = a close race.
DEFAULT_CLOSE_RACE_RANGE: tuple[float, float] = (0.40, 0.60)

# Minimum 24h volume to consider a market "high volume".
#
# Used by:
# - analysis/scanner.py: MarketScanner.scan_high_volume()
#
# Higher threshold filters out low-activity markets.
DEFAULT_HIGH_VOLUME_THRESHOLD: int = 10000

# Minimum spread (in cents) to consider a market "wide spread".
#
# Used by:
# - analysis/scanner.py: MarketScanner.scan_wide_spread()
#
# Wide spreads may indicate market-making opportunities or illiquidity.
DEFAULT_WIDE_SPREAD_THRESHOLD: int = 5

# =============================================================================
# Liquidity Analysis Thresholds
# =============================================================================

# Radius (in cents from midpoint) for orderbook depth analysis.
#
# Used by:
# - analysis/liquidity.py: orderbook_depth_score(), liquidity_score()
#
# Liquidity within this radius contributes to depth scores.
DEFAULT_DEPTH_RADIUS_CENTS: int = 10

# Maximum slippage (in cents) for "safe" order sizing.
#
# Used by:
# - analysis/liquidity.py: max_safe_order_size(), liquidity_score()
#
# Orders exceeding this slippage are flagged as potentially unsafe.
DEFAULT_MAX_SLIPPAGE_CENTS: int = 3

# Grade thresholds for liquidity classification (score boundaries).
#
# Used by:
# - analysis/liquidity.py: liquidity_score() grade assignment
#
# score >= LIQUID_THRESHOLD    -> LIQUID
# score >= MODERATE_THRESHOLD  -> MODERATE
# score >= THIN_THRESHOLD      -> THIN
# score < THIN_THRESHOLD       -> ILLIQUID
LIQUIDITY_GRADE_LIQUID_THRESHOLD: int = 76
LIQUIDITY_GRADE_MODERATE_THRESHOLD: int = 51
LIQUIDITY_GRADE_THIN_THRESHOLD: int = 26

# Spread score mapping boundaries (cents).
#
# Used by:
# - analysis/liquidity.py: _spread_score()
#
# 1c spread = perfect score (100), 20c+ spread = worst score (0).
# Linear interpolation between these bounds.
SPREAD_SCORE_BEST_CENTS: int = 1
SPREAD_SCORE_WORST_CENTS: int = 20

# Warning thresholds for liquidity analysis.
#
# Used by:
# - analysis/liquidity.py: liquidity_score() warning generation
#
# Spread warning: spread > 10c triggers "Wide spread will eat edge"
# Volume warning: volume_24h < 1000 triggers "Low volume"
# Depth warning: total_contracts < 100 triggers "Thin book"
# Imbalance warning: abs(imbalance_ratio) > 0.5 triggers "Orderbook imbalance"
LIQUIDITY_WARNING_SPREAD_CENTS: int = 10
LIQUIDITY_WARNING_VOLUME_24H: int = 1000
LIQUIDITY_WARNING_DEPTH_CONTRACTS: int = 100
LIQUIDITY_WARNING_IMBALANCE_RATIO: float = 0.5

# =============================================================================
# Agent Budget Defaults
# =============================================================================

# Default maximum spend per analysis run for Exa API calls.
#
# Used by:
# - agent/orchestrator.py: AgentKernel default budget
# - cli/agent.py: --max-exa-usd option default
#
# This bounds the cost of research lookups (search, context, topic queries).
# Set conservatively low for typical single-market analysis runs.
DEFAULT_AGENT_MAX_EXA_USD: float = 0.25

# Default maximum spend per analysis run for LLM (synthesizer) calls.
#
# Used by:
# - agent/orchestrator.py: AgentKernel default budget
# - cli/agent.py: --max-llm-usd option default
#
# This bounds the cost of LLM inference (probability synthesis, confidence).
# Set conservatively low; typical single-market synthesis is well under this.
DEFAULT_AGENT_MAX_LLM_USD: float = 0.25

# =============================================================================
# Exa API Cost Estimates (Vendor Pricing)
# =============================================================================
#
# These constants encode Exa's pricing tiers as documented in
# `docs/_vendor-docs/exa-api-reference.md`. They are used to estimate API
# call costs before execution, enabling budget enforcement.
#
# IMPORTANT: If Exa changes their pricing, update these values. The safety
# factor provides a buffer for minor pricing drift.

# Search tier boundaries (number of results).
#
# Used by:
# - exa/policy.py: estimate_search_cost_usd(), estimate_find_similar_cost_usd()
#
# Exa prices searches in two tiers: 1-25 results and 26-100 results.
EXA_SEARCH_TIER_SMALL_MAX: int = 25
EXA_SEARCH_TIER_LARGE_MAX: int = 100

# Neural search base costs (per request, not per result).
#
# Used by:
# - exa/policy.py: estimate_search_cost_usd(), estimate_find_similar_cost_usd()
#
# neuralSearch_1_25_results: $0.005
# neuralSearch_26_100_results: $0.025
EXA_NEURAL_SEARCH_COST_SMALL_USD: float = 0.005
EXA_NEURAL_SEARCH_COST_LARGE_USD: float = 0.025

# Deep search base costs (per request, not per result).
#
# Used by:
# - exa/policy.py: estimate_search_cost_usd()
#
# deepSearch_1_25_results: $0.015
# deepSearch_26_100_results: $0.075
EXA_DEEP_SEARCH_COST_SMALL_USD: float = 0.015
EXA_DEEP_SEARCH_COST_LARGE_USD: float = 0.075

# Per-result add-on costs for text/highlights.
#
# Used by:
# - exa/policy.py: estimate_search_cost_usd(), estimate_find_similar_cost_usd()
#
# Each result with full text adds $0.001; highlights adds $0.001.
EXA_PER_RESULT_TEXT_COST_USD: float = 0.001
EXA_PER_RESULT_HIGHLIGHTS_COST_USD: float = 0.001

# Answer endpoint cost estimates.
#
# Used by:
# - exa/policy.py: estimate_answer_cost_usd()
#
# Exa's /answer pricing is not as granular as /search. These are conservative
# estimates for budget enforcement.
EXA_ANSWER_WITH_TEXT_COST_USD: float = 0.05
EXA_ANSWER_WITHOUT_TEXT_COST_USD: float = 0.03

# Safety factor for cost estimates.
#
# Used by:
# - exa/policy.py: estimate_search_cost_usd(), estimate_find_similar_cost_usd()
#
# Multiplier applied to estimates to account for minor pricing drift or
# unexpected backend choices (e.g., "auto" type choosing deep search).
EXA_COST_ESTIMATE_SAFETY_FACTOR: float = 1.2
