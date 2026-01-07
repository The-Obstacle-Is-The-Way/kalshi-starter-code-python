# BUG-030: `scan arbitrage` inverse-sum returns false positives for 0/0 markets (P3)

**Priority:** P3 (Noisy output; feature credibility)
**Status:** 🟡 Open
**Found:** 2026-01-07
**Spec:** SPEC-006-event-correlation-analysis.md, SPEC-010-cli-completeness.md

---

## Summary

`kalshi scan arbitrage` can report “inverse_sum” opportunities with `100%` divergence caused by markets that have
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

---

## Impact

- Arbitrage scan output is dominated by noise (untradable markets), which hides real opportunities.

---

## Proposed Fix

- Skip/penalize unpriced or illiquid markets when computing inverse sums:
  - require `yes_ask > 0` and `yes_bid > 0` (or other “priced” heuristic)
  - require `spread <= max_spread` and/or `volume_24h/open_interest >= threshold`
- Consider extending inverse checks to events with more than two outcomes (sum over all markets).

---

## Acceptance Criteria

- `scan arbitrage` does not report inverse-sum opportunities where either leg is `0/0` quoted.
- Reported opportunities are tradable (reasonable spread and/or non-trivial volume/open interest).

