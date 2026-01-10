"""Orderbook data models for Kalshi API."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


def _dollar_to_cents(dollar_str: str) -> int:
    """
    Convert dollar string (e.g., "0.50") to cents (e.g., 50).

    This handles the Kalshi API migration from integer cents to dollar strings.
    After Jan 15, 2026, the API will only return dollar-denominated fields.
    """
    return int(Decimal(dollar_str) * 100)


class Orderbook(BaseModel):
    """
    Market orderbook snapshot.

    Note: API returns yes/no as list of [price, quantity] tuples, or null if empty.
    The API only returns bids (no asks) - use yes for YES bids, no for NO bids.

    IMPORTANT: As of Jan 15, 2026, Kalshi is deprecating the integer cents fields
    (yes, no) in favor of dollar-denominated strings (yes_dollars, no_dollars).
    The computed properties below handle both formats for backward compatibility.
    """

    model_config = ConfigDict(frozen=True)

    # Each level is [price_cents, quantity] - DEPRECATED Jan 15, 2026
    yes: list[tuple[int, int]] | None = None
    no: list[tuple[int, int]] | None = None
    # Dollar-denominated versions (e.g., [("0.50", 10), ("0.49", 5)])
    # These become the primary fields after Jan 15, 2026
    yes_dollars: list[tuple[str, int]] | None = None
    no_dollars: list[tuple[str, int]] | None = None

    @property
    def best_yes_bid(self) -> int | None:
        """
        Best YES bid price in cents.

        Prefers legacy `yes` field if present, falls back to `yes_dollars`.
        """
        # Prefer legacy cents field if available
        if self.yes:
            return max(price for price, _ in self.yes)
        # Fallback to dollar field (post Jan 15, 2026)
        if self.yes_dollars:
            return max(_dollar_to_cents(price) for price, _ in self.yes_dollars)
        return None

    @property
    def best_no_bid(self) -> int | None:
        """
        Best NO bid price in cents.

        Prefers legacy `no` field if present, falls back to `no_dollars`.
        """
        # Prefer legacy cents field if available
        if self.no:
            return max(price for price, _ in self.no)
        # Fallback to dollar field (post Jan 15, 2026)
        if self.no_dollars:
            return max(_dollar_to_cents(price) for price, _ in self.no_dollars)
        return None

    @property
    def spread(self) -> int | None:
        """
        Calculate implied spread in cents.

        Since orderbook only has bids, spread = 100 - best_yes_bid - best_no_bid.
        """
        if self.best_yes_bid is None or self.best_no_bid is None:
            return None
        return 100 - self.best_yes_bid - self.best_no_bid

    @property
    def midpoint(self) -> Decimal | None:
        """Calculate midpoint price for YES side."""
        if self.best_yes_bid is None or self.best_no_bid is None:
            return None
        # Implied YES ask = 100 - best_no_bid
        implied_yes_ask = 100 - self.best_no_bid
        return (Decimal(self.best_yes_bid) + Decimal(implied_yes_ask)) / 2
