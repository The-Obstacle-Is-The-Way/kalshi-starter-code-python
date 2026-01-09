# TODO-006: Session Friction Audit & System Improvements

**Priority**: High
**Status**: Active
**Created**: 2026-01-09

## Session Overview

This document captures all friction points encountered during a research session, categorizes the issues, and proposes systematic improvements to prevent recurrence.

---

## CATEGORY 1: Critical Research Failures

### Issue 1.1: Market Open Time Not Checked (Catastrophic)

**What Happened**:
- Exa research correctly found Stranger Things S5 released Nov-Dec 2025
- AI recommended "buy YES, it's already released"
- Market opened January 5, 2026 - AFTER S5 finished
- User bought 36 shares at 13¢ based on flawed recommendation
- This is a **catastrophic reasoning failure**

**Root Cause**:
1. Research workflow never fetched `open_time` from API
2. No temporal validation: "Is the researched event AFTER market opened?"
3. Market price signal (11-14%) was ignored - should have triggered skepticism

**Related TODO**: [TODO-005](TODO-005-market-open-date-validation.md)

**Required Fixes**:
- [ ] Add `open_time` and `created_time` to `market get` CLI output
- [ ] Research workflow must check market open time BEFORE researching
- [ ] Add skill guidance: "If market price seems too easy, verify timing"

---

### Issue 1.2: Recommending Positions User Already Owns

**What Happened**:
- User asked for 5 NEW market opportunities
- AI recommended positions user already held
- User had to explicitly call this out

**Root Cause**:
1. No query of existing portfolio before making recommendations
2. Research workflow doesn't exclude owned positions
3. Skill doesn't document: "Check portfolio first"

**Required Fix**:
- [ ] Create workflow: "Before recommending markets, run `portfolio history` to exclude owned tickers"
- [ ] Document in skill: Always check portfolio before recommending new plays

---

## CATEGORY 2: CLI Command Friction

### Issue 2.1: Ticker Guessing (404 Errors)

**What Happened**:
- Tried `CONTROLS-2026`, `KXCONTROLS-2026`, `KXCONTROLS-26`, etc.
- All returned 404 errors
- Had to fetch Kalshi website to find actual ticker `CONTROLS-2026-D`

**Root Cause**:
1. Kalshi tickers follow no consistent naming pattern
2. Skill docs don't have ticker discovery workflow
3. No "search" capability in CLI

**What Skill Says**:
- "NO `--search` option exists" ✓ (correct)
- Provides database queries ✓ (correct)
- But database only has tickers that were already synced

**Required Fixes**:
- [ ] Add to WORKFLOWS.md: "Ticker Discovery" workflow
- [ ] Add to GOTCHAS.md: "Tickers are not predictable - use Kalshi website or sync first"
- [ ] Consider adding web scraper or API search to CLI

### Issue 2.2: Scan Commands Missing Data

**What Happened**:
- `scan opportunities --filter close-race` returned "No opportunities found"
- `scan opportunities --filter high-volume` same result
- Data exists but filters returned empty

**Root Cause**:
1. May need recent sync/snapshot first
2. Filter criteria might be too strict
3. `--max-pages` workaround needed for BUG-048

**Required Fixes**:
- [ ] Add to WORKFLOWS.md: "Always sync before scan"
- [ ] Add troubleshooting for empty scan results

### Issue 2.3: Market List Status Filter Bug

**What Happened**:
- `market list --status active` returned giant error traceback
- Had to use database directly

**Investigation Needed**:
- [ ] Verify if this is a real bug or user error
- [ ] If bug, document in _bugs/

---

## CATEGORY 3: Database Schema Knowledge Gap

### Issue 3.1: Queried Non-Existent Columns

**What Happened**:
- Tried: `SELECT ticker, title, yes_bid, yes_ask, volume_24h FROM markets`
- Error: `no such column: yes_bid`

**Root Cause**:
1. Markets table only has static metadata
2. Price/volume data is in `price_snapshots` table
3. Skill's DATABASE.md doesn't clearly explain this separation

**Required Fixes**:
- [ ] Update DATABASE.md: Explain markets vs price_snapshots distinction
- [ ] Add query examples for "get current prices for markets"
- [ ] Document join pattern: markets JOIN price_snapshots

---

## CATEGORY 4: Bugs Discovered

### BUG-048: Negative Liquidity Validation (Already Documented)

**What Happened**:
- Full market scan crashed with ValidationError
- `liquidity` field in API returns negative values (e.g., -170750)
- Pydantic model has `ge=0` constraint

**Workaround**: Use `--max-pages` to limit pagination

**Status**: Documented in [BUG-048](../bugs/BUG-048-negative-liquidity-validation.md)

### BUG-047: Portfolio Positions Sync (Already Documented)

**What Happened**:
- `portfolio sync` reports "0 positions"
- `portfolio balance` shows $87.37 portfolio value
- 9 trades successfully synced

**Status**: Documented in [BUG-047](../bugs/BUG-047-portfolio-positions-sync.md)

---

## CATEGORY 5: Skill Documentation Gaps

### Gap 5.1: No "Research Workflow" in WORKFLOWS.md

The skill has CLI commands but lacks an end-to-end research workflow:

**Missing Workflow**:
```
1. Check portfolio first (what do I already own?)
2. Identify market of interest
3. Fetch market details INCLUDING open_time
4. Validate timing: Is the event AFTER market opened?
5. Run Exa research ONLY for events after open_time
6. Cross-validate: Does price make sense given research?
7. If price seems too easy, investigate why
8. Make recommendation
```

### Gap 5.2: No "Portfolio-Aware Research" Guidance

**Missing Guidance**:
- Before recommending, exclude positions from `portfolio history`
- When user asks for "new opportunities", this means positions they don't own

### Gap 5.3: No "Price as Signal" Heuristic

**Missing Guidance**:
- If market price suggests 10-15% probability but research says "obvious YES", STOP
- Market price disagreement is a signal to investigate deeper
- Look for what the market knows that research might miss

---

## CATEGORY 6: Future Enhancements (TO-DO items)

### Enhancement 6.1: Portfolio-Aware Alerts

**Concept**: Monitor positions user already owns for adverse movement

**Implementation**:
- Alert when owned position price drops significantly
- Alert when new research contradicts existing thesis
- Requires linking alerts to portfolio

### Enhancement 6.2: Research Validation Pipeline

**Concept**: Automated checks before recommending

**Validation Steps**:
1. Check `open_time` vs researched events
2. Check if user already owns position
3. Flag if price seems inconsistent with research
4. Require human confirmation for "easy money" conclusions

---

## Action Items Summary

### Immediate (Fix Skill Docs)

1. [ ] Update WORKFLOWS.md: Add "Research Workflow" with temporal validation
2. [ ] Update WORKFLOWS.md: Add "Ticker Discovery" workflow
3. [ ] Update GOTCHAS.md: Add "Price as Signal" heuristic
4. [ ] Update GOTCHAS.md: Add "Market Timing" gotcha (open_time matters)
5. [ ] Update GOTCHAS.md: Add "Portfolio-Aware Research" guidance
6. [ ] Update DATABASE.md: Clarify markets vs price_snapshots schema

### Code Fixes (TODO-005)

7. [ ] Add `open_time` and `created_time` to `market get` output
8. [ ] Research commands should optionally fetch market timing

### Bug Fixes

9. [ ] Fix BUG-048: Negative liquidity validation
10. [ ] Investigate BUG-047: Portfolio sync discrepancy
11. [ ] Investigate `market list --status active` error

### Future Enhancements

12. [ ] Portfolio-aware alert system
13. [ ] Research validation pipeline
14. [ ] Ticker search/discovery CLI feature

---

## Lessons Learned

1. **Always check `open_time` for time-sensitive markets** - Events that happened before market opened don't count
2. **Market price is information** - If price disagrees with research, investigate
3. **Check portfolio first** - Before recommending, know what user owns
4. **Skill docs need workflows, not just commands** - End-to-end guidance prevents errors
5. **Database schema must be clear** - Which table has what data

---

## Related Files

- TODO-005: [Market Open Date Validation](TODO-005-market-open-date-validation.md)
- BUG-047: [Portfolio Positions Sync](../bugs/BUG-047-portfolio-positions-sync.md)
- BUG-048: [Negative Liquidity Validation](../bugs/BUG-048-negative-liquidity-validation.md)
- SKILL.md: `.claude/skills/kalshi-cli/SKILL.md`
- WORKFLOWS.md: `.claude/skills/kalshi-cli/WORKFLOWS.md`
- GOTCHAS.md: `.claude/skills/kalshi-cli/GOTCHAS.md`
- DATABASE.md: `.claude/skills/kalshi-cli/DATABASE.md`
