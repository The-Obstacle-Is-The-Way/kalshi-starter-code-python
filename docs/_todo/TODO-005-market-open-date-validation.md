# TODO-005: Market Open Date Validation for Research Recommendations

**Priority**: High
**Status**: PARTIAL - 1/3 criteria complete
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

### 1. CLI Enhancement: Add `open_time` to Market Display ✅ COMPLETE

**File**: `src/kalshi_research/cli/market.py`
**Commit**: `d7a9694` (2026-01-09)

The `market get` command now displays:
- `open_time` - when trading started
- `created_time` - when market was created (if present)
- `close_time` - market expiration

### 2. Research Workflow: Temporal Validation ❌ NOT STARTED

**File**: `src/kalshi_research/research/thesis.py`

When researching time-sensitive markets (media releases, events, elections), the workflow MUST:

1. Fetch market `open_time` first
2. Only research events that occurred AFTER `open_time`
3. Flag if researched events predate market opening

**Implementation Guidance:**

```python
# In thesis.py or a new temporal_validator.py
def validate_research_temporal_alignment(
    market: Market,
    event_date: datetime,
) -> TemporalValidationResult:
    """
    Check if researched event occurred after market opened.

    Returns warning if event predates market.open_time.
    """
    if event_date < market.open_time:
        return TemporalValidationResult(
            valid=False,
            warning=f"Event ({event_date}) predates market open ({market.open_time}). "
                    "This event likely does NOT count for this market."
        )
    return TemporalValidationResult(valid=True)
```

### 3. Documentation: Add Warning to GOTCHAS.md ❌ NOT STARTED

**File**: `.claude/skills/kalshi-cli/GOTCHAS.md`

Add section:

```markdown
## Market Timing Trap

**Problem**: Markets asking "Will X happen before Y?" only count events AFTER market opens.

**Example**: Stranger Things S5 released Dec 2025, but market asking about "new episode"
opened Jan 2026. S5 doesn't count - market is asking about S6 or beyond.

**Prevention**:
1. Always run `kalshi market get <ticker>` first
2. Check `Open Time` before researching
3. If researched event predates open_time, it DOES NOT COUNT
4. Be suspicious if price seems "too good" (11-14% for "sure thing" = red flag)
```

## Lessons Learned

1. **Market price is signal** - 11-14% should have triggered suspicion
2. **Check open_time FIRST** - before any research
3. **Cross-validate** - if research says "obvious win" but price disagrees, dig deeper

## Related Files

- `src/kalshi_research/cli/market.py` - market display commands ✅
- `src/kalshi_research/api/client.py` - API data fetching
- `src/kalshi_research/research/thesis.py` - research tools ❌
- `.claude/skills/kalshi-cli/GOTCHAS.md` - gotchas documentation ❌

## Acceptance Criteria

- [x] `market get` displays `open_time` and `created_time` (commit: d7a9694)
- [ ] Research workflow includes temporal validation
- [ ] Documentation updated with market timing warnings in GOTCHAS.md
