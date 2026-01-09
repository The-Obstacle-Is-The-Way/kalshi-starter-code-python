# BUG-047: Portfolio Positions Sync Discrepancy

**Priority**: Medium
**Status**: Investigating
**Created**: 2026-01-09

## Symptom

`uv run kalshi portfolio sync` reports "Synced 0 positions" and `portfolio positions` shows "No open positions found", but `portfolio balance` shows a non-zero `portfolio_value` ($87.37).

## Context

- 9 trades were successfully synced to the database
- All markets appear to still be active (checked KXNCAAFSPREAD-26JAN09OREIND-IND3, status=active)
- Balance API returns: balance=10666, portfolio_value=8737

## Possible Causes

1. API positions endpoint returning empty while balance endpoint shows value
2. Sync logic filtering out positions incorrectly
3. Kalshi API inconsistency between endpoints
4. Positions may be computed differently by Kalshi

## Next Steps

1. Investigate `portfolio/syncer.py` sync_positions method
2. Add debug logging to see raw API response
3. Compare raw positions API response vs balance API response
4. Check if Kalshi calculates portfolio_value from fills/orders rather than positions

## Related Files

- `src/kalshi_research/portfolio/syncer.py`
- `src/kalshi_research/api/client.py`
