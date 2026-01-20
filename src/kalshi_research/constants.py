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
