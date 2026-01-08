# BUG-030: `scan arbitrage` inverse-sum returns false positives for 0/0 markets (P3)

**Priority:** P3 (Noisy output; feature credibility)
**Status:** 🟢 Fixed (2026-01-07)
**Found:** 2026-01-07
**Spec:** SPEC-006-event-correlation-analysis.md, SPEC-010-cli-completeness.md
**Checklist Ref:** CODE_AUDIT_CHECKLIST.md Section 17 (Floating Point), Section 18 (NumPy/Pandas Silent Failures)

---

## Summary

`kalshi scan arbitrage` can report "inverse_sum" opportunities with `100%` divergence caused by markets that have
no meaningful quotes (both legs `yes_bid=0` and `yes_ask=0`).

---

## Reproduction

```bash
uv run python - <<'PY'
import asyncio
from kalshi_research.api import KalshiPublicClient
from kalshi_research.analysis.correlation import CorrelationAnalyzer

async def main() -> None:
    async with KalshiPublicClient() as client:
        markets = [m async for m in client.get_all_markets(status="open")]

    analyzer = CorrelationAnalyzer()
    pairs = analyzer.find_inverse_markets(markets, tolerance=0.10)
    pairs.sort(key=lambda t: abs(t[2]), reverse=True)

    for m1, m2, dev in pairs[:5]:
        print(m1.ticker, m1.yes_bid, m1.yes_ask, "|", m2.ticker, m2.yes_bid, m2.yes_ask, "dev", dev)

asyncio.run(main())
PY
```

Observed pattern (examples):

- both legs `yes_bid=0` and `yes_ask=0`
- deviation `-1.0` (sum of midpoints is `0.0`), displayed as `100%` divergence

---

## Root Cause

`CorrelationAnalyzer.find_inverse_markets()` uses bid/ask midpoints as probabilities without validating that a
market is actually priced/tradable. Midpoints from `0/0` quotes are treated as `0.0`.

**Best Practice Violation:**
- [CME Liquidity Assessment 2025](https://www.cmegroup.com/articles/2025/reassessing-liquidity-beyond-order-book-depth.html) —
  Markets without quotes have no meaningful price
- [Bid-Ask Spread Research](https://academic.oup.com/rfs/article/30/12/4437/4047344) — Discard days with zero
  price range when computing spreads

---

## Impact

- Arbitrage scan output is dominated by noise (untradable markets), which hides real opportunities.

---

## Ironclad Fix Specification

**Approach:** Add `_is_priced()` helper to filter unpriced/illiquid markets.

**File:** `src/kalshi_research/analysis/correlation.py`

**Add helper function:**

```python
def _is_priced(market: Market, min_spread: int = 1) -> bool:
    """
    Check if a market has meaningful price discovery.

    A market is considered "priced" if:
    - Both bid and ask are non-zero (someone is willing to trade)
    - OR at least one of bid/ask is non-zero with reasonable spread

    Args:
        market: Market to check
        min_spread: Minimum spread to consider "priced" (default: 1)

    Returns:
        True if market has meaningful quotes
    """
    # Completely unpriced (no quotes at all)
    if market.yes_bid == 0 and market.yes_ask == 0:
        return False

    # Placeholder quotes (0/100 = no real price discovery)
    if market.yes_bid == 0 and market.yes_ask == 100:
        return False

    # Has at least some price discovery
    return True
```

**Change `find_inverse_markets()` method (lines 231-273):**

```python
def find_inverse_markets(
    self,
    markets: list[Market],
    tolerance: float = 0.05,
) -> list[tuple[Market, Market, float]]:
    """
    Find market pairs that should sum to ~100% (inverse relationship).

    Common examples:
    - Trump vs Biden (should sum to ~100%)
    - BTC above X vs below X

    Args:
        markets: List of markets to analyze
        tolerance: Allowed deviation from 100%

    Returns:
        List of (market_a, market_b, sum_deviation) tuples
    """
    results: list[tuple[Market, Market, float]] = []

    # Group by event
    by_event: dict[str, list[Market]] = {}
    for m in markets:
        # SKIP: Unpriced markets (0/0, 0/100 placeholder quotes)
        if not _is_priced(m):
            continue

        event_ticker = m.event_ticker
        if event_ticker not in by_event:
            by_event[event_ticker] = []
        by_event[event_ticker].append(m)

    # Check pairs within same event
    for event_markets in by_event.values():
        if len(event_markets) == 2:
            m1, m2 = event_markets
            # Use midpoint of bid/ask as price
            price1 = (m1.yes_bid + m1.yes_ask) / 2.0 / 100.0
            price2 = (m2.yes_bid + m2.yes_ask) / 2.0 / 100.0
            prob_sum = price1 + price2

            if abs(prob_sum - 1.0) > tolerance:
                deviation = prob_sum - 1.0
                results.append((m1, m2, deviation))

    return results
```

---

## Acceptance Criteria

- [x] `find_inverse_markets()` skips markets with `yes_bid=0, yes_ask=0` (unpriced)
- [x] `find_inverse_markets()` skips markets with `yes_bid=0, yes_ask=100` (placeholder)
- [x] `_is_priced()` helper function added and tested (`tests/unit/analysis/test_correlation.py::TestIsPriced`)
- [x] Unit tests cover inverse filtering (`tests/unit/analysis/test_correlation.py::TestFindInverseMarkets`)

---

## Test Plan

```python
def test_find_inverse_markets_excludes_unpriced() -> None:
    """Unpriced markets (0/0) should be excluded from inverse detection."""
    markets = [
        # Event A: Both priced - should be detected
        make_market(ticker="A_YES", event_ticker="A", yes_bid=60, yes_ask=65),
        make_market(ticker="A_NO", event_ticker="A", yes_bid=30, yes_ask=35),
        # Event B: One unpriced - should be excluded
        make_market(ticker="B_YES", event_ticker="B", yes_bid=50, yes_ask=55),
        make_market(ticker="B_NO", event_ticker="B", yes_bid=0, yes_ask=0),
    ]

    analyzer = CorrelationAnalyzer()
    pairs = analyzer.find_inverse_markets(markets, tolerance=0.10)

    event_tickers = [m1.event_ticker for m1, m2, _ in pairs]
    assert "A" in event_tickers
    assert "B" not in event_tickers


def test_find_inverse_markets_excludes_placeholder_quotes() -> None:
    """Placeholder quotes (0/100) should be excluded from inverse detection."""
    markets = [
        make_market(ticker="C_YES", event_ticker="C", yes_bid=50, yes_ask=55),
        make_market(ticker="C_NO", event_ticker="C", yes_bid=0, yes_ask=100),  # Placeholder
    ]

    analyzer = CorrelationAnalyzer()
    pairs = analyzer.find_inverse_markets(markets, tolerance=0.10)

    assert len(pairs) == 0  # Event C excluded due to placeholder


def test_is_priced_helper() -> None:
    """Test _is_priced() helper function."""
    from kalshi_research.analysis.correlation import _is_priced

    # Unpriced
    assert not _is_priced(make_market(yes_bid=0, yes_ask=0))
    # Placeholder
    assert not _is_priced(make_market(yes_bid=0, yes_ask=100))
    # Priced
    assert _is_priced(make_market(yes_bid=45, yes_ask=55))
    assert _is_priced(make_market(yes_bid=1, yes_ask=99))
```
