# BUG-089: Negative Liquidity Warnings Spam Logs/Console Output

## Priority: P4 (Cosmetic)

## Summary
When commands fetch many markets (e.g., `kalshi scan opportunities`, `kalshi scan arbitrage`), parsing markets can emit **hundreds of warnings** like:

```text
Received negative liquidity value: -39765. Treating as None. Field deprecated Jan 15, 2026.
Received negative liquidity value: -16116. Treating as None. Field deprecated Jan 15, 2026.
... (100+ more lines)
```

## Impact
- Console output is difficult to read
- Actual scan results get buried under warning spam
- Log files grow unnecessarily large

## Root Cause
Kalshi deprecated the integer `liquidity` field (see inline note in the model). In production, we observe negative `liquidity` values and treat them as `None`.

Our `Market` model handles this correctly, but it logs a warning **once per market**, which becomes noisy for bulk scans.

## Recommended Fix
1. Log this warning once per session, not per-market
2. Or demote to debug level after first occurrence
3. Consider removing the warning entirely since we handle the deprecated field correctly

## Affected Code
- `src/kalshi_research/api/models/market.py` (`Market.handle_deprecated_liquidity`)

## Workaround
- Set `KALSHI_LOG_LEVEL=ERROR` to suppress warnings, or redirect stderr (logs) away.

## Discovered
2026-01-21 during stress test session

## Status
Open
