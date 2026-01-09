# BUG-029: `scan opportunities --filter close-race` returns illiquid/unpriced markets (P2)

**Priority:** P2 (Core feature produces misleading output)
**Status:** 🟢 Fixed (2026-01-07)
**Found:** 2026-01-07
**Spec:** SPEC-010-cli-completeness.md
**Checklist Ref:** code-audit-checklist.md Section 17 (Floating Point), Section 18 (NumPy/Pandas Silent Failures)

---

## Summary

The "close-race" scanner currently surfaces markets with:

- `volume_24h = 0`
- Extreme spreads (often `100¢`)
- Often placeholder pricing (e.g., `yes_bid=0`, `yes_ask=100`)

This makes the output largely non-actionable and actively misleading for "find interesting markets" workflows.

---

## Reproduction

```bash
uv run kalshi scan opportunities --filter close-race --top 20
```

Example observed result pattern (from live API on 2026-01-07):

- `prob = 0.500`, `spread = 100`, `volume_24h = 0`

---

## Root Cause

`MarketScanner.scan_close_races()` computes probability as the midpoint of bid/ask:

- `(yes_bid + yes_ask) / 200`

For illiquid markets with quotes like `0/100`, the midpoint is exactly `0.5`, so they rank as "closest to 50%"
even though there is no meaningful price discovery.

**Best Practice Violation:**
- [CME Liquidity Assessment 2025](https://www.cmegroup.com/articles/2025/reassessing-liquidity-beyond-order-book-depth.html) —
  Midpoint is meaningless in illiquid markets; use multiple metrics
- [Bloomberg Midpoint Fair Price](https://www.bloomberg.com/professional/insights/trading/mid-point-fairer-price/) —
  "In illiquid markets, the midpoint is meaningless"
- [Trading Illiquid Options](https://predictingalpha.com/illiquid-options/) — Wide spreads = unreliable fair value

---

## Impact

- "Opportunities" scans are dominated by dead/unpriced markets.
- Users can waste time and/or make incorrect decisions based on meaningless probabilities.

---

## Ironclad Fix Specification

**Approach:** Add liquidity guards to filter out unpriced/illiquid markets before ranking.

**File:** `src/kalshi_research/analysis/scanner.py`

**Change `scan_close_races()` method (lines 77-122):**

```python
def scan_close_races(
    self,
    markets: list[Market],
    top_n: int = 10,
    min_volume_24h: int = 0,      # ADD: Liquidity filter
    max_spread: int = 100,        # ADD: Spread filter (100 = no filter)
) -> list[ScanResult]:
    """
    Find markets near 50% probability.

    These are the most uncertain markets - ideal for
    research and finding edges.

    Args:
        markets: List of markets to scan
        top_n: Number of results to return
        min_volume_24h: Minimum 24h volume (default: 0)
        max_spread: Maximum bid-ask spread in cents (default: 100)

    Returns:
        List of ScanResults sorted by closeness to 50%
    """
    results: list[ScanResult] = []

    for m in markets:
        # SKIP: Unpriced markets (0/0 or 0/100 placeholder quotes)
        if m.yes_bid == 0 and m.yes_ask == 0:
            continue  # No quotes at all
        if m.yes_bid == 0 and m.yes_ask == 100:
            continue  # Placeholder: no real price discovery

        spread = m.yes_ask - m.yes_bid

        # SKIP: Illiquid markets
        if spread > max_spread:
            continue
        if m.volume_24h < min_volume_24h:
            continue

        # Calculate probability from midpoint
        prob = (m.yes_bid + m.yes_ask) / 200.0

        # Check if in close race range
        if self.close_race_range[0] <= prob <= self.close_race_range[1]:
            # Score by closeness to 50%
            score = 1.0 - abs(prob - 0.5) * 2

            results.append(
                ScanResult(
                    ticker=m.ticker,
                    title=m.title,
                    filter_type=ScanFilter.CLOSE_RACE,
                    score=score,
                    market_prob=prob,
                    volume_24h=m.volume_24h,
                    spread=spread,
                    details={"distance_from_50": abs(prob - 0.5)},
                )
            )

    # Sort by score (closest to 50% first)
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_n]
```

**CLI Changes:**

Add `--min-volume` and `--max-spread` flags to `scan opportunities` command.

---

## Acceptance Criteria

- [x] `scan_close_races()` skips markets with `yes_bid=0, yes_ask=0` (unpriced)
- [x] `scan_close_races()` skips markets with `yes_bid=0, yes_ask=100` (placeholder)
- [x] `--min-volume` flag filters markets below threshold
- [x] `--max-spread` flag filters markets with wide spreads
- [x] Unit tests cover placeholder/filters (`tests/unit/analysis/test_scanner.py`)

---

## Test Plan

```python
def test_scan_close_races_excludes_unpriced_markets() -> None:
    """Unpriced markets (0/0, 0/100) should be excluded."""
    markets = [
        make_market(ticker="PRICED", yes_bid=45, yes_ask=55, volume_24h=1000),
        make_market(ticker="UNPRICED_00", yes_bid=0, yes_ask=0, volume_24h=0),
        make_market(ticker="PLACEHOLDER", yes_bid=0, yes_ask=100, volume_24h=0),
    ]

    scanner = MarketScanner()
    results = scanner.scan_close_races(markets, top_n=10)

    tickers = [r.ticker for r in results]
    assert "PRICED" in tickers
    assert "UNPRICED_00" not in tickers
    assert "PLACEHOLDER" not in tickers


def test_scan_close_races_respects_min_volume() -> None:
    """Markets below min_volume_24h should be excluded."""
    markets = [
        make_market(ticker="HIGH_VOL", yes_bid=45, yes_ask=55, volume_24h=10000),
        make_market(ticker="LOW_VOL", yes_bid=45, yes_ask=55, volume_24h=100),
    ]

    scanner = MarketScanner()
    results = scanner.scan_close_races(markets, top_n=10, min_volume_24h=1000)

    tickers = [r.ticker for r in results]
    assert "HIGH_VOL" in tickers
    assert "LOW_VOL" not in tickers


def test_scan_close_races_respects_max_spread() -> None:
    """Markets with spread > max_spread should be excluded."""
    markets = [
        make_market(ticker="TIGHT", yes_bid=48, yes_ask=52, volume_24h=1000),  # spread=4
        make_market(ticker="WIDE", yes_bid=20, yes_ask=80, volume_24h=1000),   # spread=60
    ]

    scanner = MarketScanner()
    results = scanner.scan_close_races(markets, top_n=10, max_spread=10)

    tickers = [r.ticker for r in results]
    assert "TIGHT" in tickers
    assert "WIDE" not in tickers
```
