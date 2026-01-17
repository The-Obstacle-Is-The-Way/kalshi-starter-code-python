"""Orderbook data models for Kalshi API."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from .pricing import fixed_dollars_to_cents


def _dollar_to_cents(dollar_str: str) -> int:
    """
    Convert dollar string (e.g., "0.50") to cents (e.g., 50).

    This handles the Kalshi API migration from integer cents to dollar strings.
    As of Jan 2026, `*_dollars` fields are the SSOT; legacy integer-cent arrays may still
    appear during soft deprecation, but are not used for computed properties.
    """
    return fixed_dollars_to_cents(dollar_str, label="orderbook price")


class Orderbook(BaseModel):
    """
    Market orderbook snapshot.

    Note: API returns yes/no as list of [price, quantity] tuples, or null if empty.
    The API only returns bids (no asks) - use yes for YES bids, no for NO bids.

    IMPORTANT: As of Jan 2026, `yes_dollars` / `no_dollars` are the SSOT. The legacy integer-cent
    arrays (`yes`, `no`) may still appear during soft deprecation, but computed properties use
    dollar fields only.
    """

    model_config = ConfigDict(frozen=True)

    # Each level is [price_cents, quantity] - DEPRECATED Jan 15, 2026
    yes: list[tuple[int, int]] | None = None
    no: list[tuple[int, int]] | None = None
    # Dollar-denominated versions (e.g., [("0.50", 10), ("0.49", 5)])
    # Prefer these when present (soft deprecation of cents fields as of Jan 15, 2026).
    yes_dollars: list[tuple[str, int]] | None = None
    no_dollars: list[tuple[str, int]] | None = None

    @property
    def yes_levels(self) -> list[tuple[int, int]]:
        """
        YES bid levels as [(price_cents, quantity), ...].

        Derived from dollar-denominated `yes_dollars`.
        """
        if not self.yes_dollars:
            return []
        return [(_dollar_to_cents(price), qty) for price, qty in self.yes_dollars]

    @property
    def no_levels(self) -> list[tuple[int, int]]:
        """
        NO bid levels as [(price_cents, quantity), ...].

        Derived from dollar-denominated `no_dollars`.
        """
        if not self.no_dollars:
            return []
        return [(_dollar_to_cents(price), qty) for price, qty in self.no_dollars]

    @property
    def best_yes_bid(self) -> int | None:
        """
        Best YES bid price in cents.

        Derived from dollar-denominated `yes_dollars`.
        """
        levels = self.yes_levels
        if levels:
            return max(price for price, _ in levels)
        return None

    @property
    def best_no_bid(self) -> int | None:
        """
        Best NO bid price in cents.

        Derived from dollar-denominated `no_dollars`.
        """
        levels = self.no_levels
        if levels:
            return max(price for price, _ in levels)
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
