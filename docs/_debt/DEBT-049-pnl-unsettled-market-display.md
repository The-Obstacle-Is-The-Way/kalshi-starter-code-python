# DEBT-049: P&L Display for Unsettled Markets

## Priority: P2 (Medium)

## Summary

The `portfolio pnl` command shows cumulative realized P&L, but it's unclear how unsettled (inactive but not finalized) markets are handled. This caused confusion when analyzing recent Trump word-mention bet outcomes.

## Observed Behavior

1. **Markets in "inactive" state** (closed for trading, awaiting settlement) still show in `portfolio positions` with unrealized P&L
2. **Realized P&L** reflects cumulative history, not recent session
3. **User won bets** but markets haven't finalized yet - unclear when/how these wins will reflect in realized P&L

## Questions to Investigate

1. **Does `portfolio sync` pull settlement data?** Or only trades/positions?
2. **What triggers realized P&L update?** Market finalization? Manual settlement sync?
3. **Is there a `sync-settlements` command?** Check if it exists and when to run it
4. **Kalshi API docs:** How does the API report settled positions vs pending settlement?

## Quick Finding

The command `kalshi data sync-settlements` exists and syncs settled market outcomes:
```bash
uv run kalshi data sync-settlements  # Syncs settlements from Kalshi API
```

**Likely workflow:**
1. `portfolio sync` - pulls positions/trades
2. `data sync-settlements` - pulls settlement outcomes (after markets finalize)
3. `portfolio pnl` - shows updated realized P&L

**Remaining question:** Is this documented? Should `portfolio pnl` prompt user to run sync-settlements if it detects stale settlement data?

## Potential Issues

1. **UX confusion:** User doesn't know when to expect P&L to update
2. **Documentation gap:** Workflow for tracking settled vs unsettled not documented

## Discovered

2026-01-21 during Trump word-mention bet analysis session

## Status

Open - Needs investigation

## Related

- Previous work: [DEBT-030](../_archive/debt/DEBT-030-trading-fees-from-settlements.md) - Trading Fees from Settlements (resolved)
- Previous work: [DEBT-029](../_archive/debt/DEBT-029-settlement-synthetic-fill-reconciliation.md) - Settlement Reconciliation (resolved)
