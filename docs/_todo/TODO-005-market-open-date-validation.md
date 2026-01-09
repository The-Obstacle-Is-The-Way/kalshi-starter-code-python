# TODO-005: Market Open Date Validation for Research Recommendations

**Priority**: High
**Status**: Active
**Created**: 2026-01-09
**Spec**: [SPEC-025: Market Open Time Display](../_specs/SPEC-025-market-open-time-display.md)

## Problem Statement

The Exa-powered research tool gave a **catastrophically wrong recommendation** on the Stranger Things market (KXMEDIARELEASEST-27JAN01) because it failed to check when the market opened.

### What Happened

1. User asked for market recommendations
2. Exa research correctly identified that Stranger Things S5 released Nov 26 - Dec 31, 2025
3. AI concluded "buy YES, it's already released, easy money"
4. **CRITICAL MISS**: Market opened **January 5, 2026** - AFTER S5 finished
5. The market is asking about NEW content beyond S5, not S5 itself
6. User bought 36 shares at 13¢ based on this flawed recommendation

### Root Cause

The research workflow does not include:
1. Checking market `open_time` / `created_time` from API
2. Cross-referencing event timing with market creation date
3. Validating that the researched event occurred AFTER market opened

### The Actual Market

```json
{
  "ticker": "KXMEDIARELEASEST-27JAN01",
  "title": "Will A New Episode of Stranger Things be released Worldwide before Jan 1, 2027?",
  "created_time": "2026-01-05T17:50:26",
  "open_time": "2026-01-05T20:00:00Z",
  "yes_bid": 12,
  "yes_ask": 14
}
```

Market opened Jan 5, 2026. S5 finale was Dec 31, 2025. Therefore S5 does NOT count.

## Required Fixes

### 1. CLI Enhancement: Add `open_time` to Market Display

**File**: `src/kalshi_research/cli/market.py`

The `market get` command **currently only shows `Close Time`** but should also display:
- `open_time` - when trading started
- `created_time` - when market was created

**Current output** (missing open_time):
```
│ Close Time    │ 2027-01-01T04:59:00+00:00                                    │
```

**Needed output**:
```
│ Open Time     │ 2026-01-05T20:00:00+00:00                                    │
│ Created Time  │ 2026-01-05T17:50:26+00:00                                    │
│ Close Time    │ 2027-01-01T04:59:00+00:00                                    │
```

This helps users understand temporal context for research.

### 2. Research Workflow: Temporal Validation

When researching time-sensitive markets (media releases, events, elections), the workflow MUST:

1. Fetch market `open_time` first
2. Only research events that occurred AFTER `open_time`
3. Flag if researched events predate market opening

### 3. Documentation: Add Warning to Research Commands

Add documentation noting that market timing matters:
- Markets asking "Will X happen before Y?" only count events AFTER market opens
- Always verify `open_time` for conditional markets

## Current Position Assessment

**Stranger Things Market (KXMEDIARELEASEST-27JAN01)**

- User owns: 36 shares YES at 13¢ ($4.68 cost)
- Current: 12-14¢
- Potential loss if NO: ~$4.68

**Note**: The purpose of this TODO is the *engineering* failure (missing market timing validation), not market advice. Any content/release-date claims should be treated as unverified unless linked to primary sources.

## Lessons Learned

1. **Market price is signal** - 11-14% should have triggered suspicion
2. **Check open_time FIRST** - before any research
3. **Cross-validate** - if research says "obvious win" but price disagrees, dig deeper

## Related Files

- `src/kalshi_research/cli/market.py` - market display commands
- `src/kalshi_research/api/client.py` - API data fetching
- `src/kalshi_research/research/` - research tools

## Acceptance Criteria

- [ ] `market get` displays `open_time` and `created_time`
- [ ] Research workflow includes temporal validation
- [ ] Documentation updated with market timing warnings
