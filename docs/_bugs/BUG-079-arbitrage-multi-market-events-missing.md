# BUG-079: Multi-Market Events Missing from Arbitrage Detection

**Status:** Open
**Priority:** P3 (Low - Feature Gap)
**Created:** 2026-01-13
**Found by:** Deep Audit
**Effort:** ~1 hour

---

## Summary

The `find_inverse_markets()` function in the correlation analyzer only detects arbitrage opportunities when an event has exactly 2 markets. Events with 3+ markets (e.g., "Who will win: A, B, or C?") are not checked for sum-to-100% arbitrage.

---

## Impact

- **Severity:** Low - Feature limitation, not a bug
- **Financial Impact:** Potential missed arbitrage opportunities
- **User Impact:** Incomplete arbitrage scanning

Kalshi has many multi-choice events where all outcomes should sum to ~100%. Examples:
- Presidential primaries (multiple candidates)
- "Which team will win the championship?" (multiple teams)
- Bracket-style markets

These represent real arbitrage opportunities that the scanner misses.

---

## Root Cause

At `src/kalshi_research/analysis/correlation.py:284-296`:

```python
# Check pairs within same event
for event_markets in by_event.values():
    if len(event_markets) == 2:  # BUG: Only handles 2-market events
        m1, m2 = event_markets
        price1 = m1.midpoint / 100.0
        price2 = m2.midpoint / 100.0
        prob_sum = price1 + price2

        if abs(prob_sum - 1.0) > tolerance:
            deviation = prob_sum - 1.0
            results.append((m1, m2, deviation))
```

---

## Expected Behavior

For events with N markets, check if `sum(probabilities) ≈ 1.0`:

```python
for event_markets in by_event.values():
    if len(event_markets) < 2:
        continue

    prices = [m.midpoint / 100.0 for m in event_markets]
    prob_sum = sum(prices)

    if abs(prob_sum - 1.0) > tolerance:
        deviation = prob_sum - 1.0
        # Return the event markets and deviation
        results.append((event_markets, deviation))
```

---

## Fix

```python
def find_inverse_markets(
    self,
    markets: list[Market],
    tolerance: float = 0.05,
) -> list[tuple[list[Market], float]]:  # Changed return type
    """
    Find market groups that should sum to ~100% (inverse relationship).

    Now handles events with 2+ markets.
    """
    results: list[tuple[list[Market], float]] = []

    by_event: dict[str, list[Market]] = {}
    for m in markets:
        if not _is_priced(m):
            continue
        event_ticker = m.event_ticker
        by_event.setdefault(event_ticker, []).append(m)

    for event_markets in by_event.values():
        if len(event_markets) < 2:
            continue

        prices = [m.midpoint / 100.0 for m in event_markets]
        prob_sum = sum(prices)

        if abs(prob_sum - 1.0) > tolerance:
            deviation = prob_sum - 1.0
            results.append((event_markets, deviation))

    return results
```

**Note:** This changes the return type signature, so callers in `cli/scan.py` need updates.

---

## Verification

```python
def test_find_inverse_markets_multi_choice():
    """Events with 3+ markets should be detected."""
    markets = [
        make_market(ticker="A", event_ticker="EVT", yes_bid=30, yes_ask=32),
        make_market(ticker="B", event_ticker="EVT", yes_bid=30, yes_ask=32),
        make_market(ticker="C", event_ticker="EVT", yes_bid=30, yes_ask=32),
    ]
    # Sum = 3 * 31 / 100 = 0.93, deviation from 1.0 = -0.07
    analyzer = CorrelationAnalyzer()
    results = analyzer.find_inverse_markets(markets, tolerance=0.05)
    assert len(results) == 1
    assert len(results[0][0]) == 3
```

---

## Migration Notes

This is a breaking change to the return type. The CLI code at `cli/scan.py:974-988` needs to handle the new format:

```python
# Old: for m1, m2, deviation in analyzer.find_inverse_markets(...)
# New: for markets, deviation in analyzer.find_inverse_markets(...)
```

---

## API Dependency Note

**This fix is enhanced by SPEC-037 Phase 2 (`GET /events/multivariate`).**

Currently, multi-market events (MVEs) are **excluded** from the standard `/events` endpoint. This means:

1. The current arbitrage scanner fetches markets via `GET /events` + nested markets
2. MVEs (multi-choice events like "Who will win: A, B, or C?") are not returned
3. Even after fixing this bug, MVE arbitrage opportunities won't be detected

**Full fix requires:**
1. This bug fix (handle N-market events, not just 2-market)
2. SPEC-037 Phase 2.1 (`GET /events/multivariate`) to fetch MVE data

See:
- `docs/_specs/SPEC-037-kalshi-missing-endpoints-phase1.md` (Phase 2.1)
- `docs/_debt/DEBT-015-missing-api-endpoints.md` (Section 12)

---

## Cross-References

| Item | Relationship |
|------|--------------|
| SPEC-037 Phase 2.1 | `GET /events/multivariate` endpoint needed for full coverage |
| DEBT-015 Section 12 | Documents MVE endpoint as P2 priority |
| `docs/_vendor-docs/kalshi-api-reference.md` | SSOT for API |
