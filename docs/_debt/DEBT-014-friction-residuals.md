# DEBT-014: Friction Residuals - Research Pipeline & Agent Design

**Priority:** Medium (Research effectiveness)
**Status:** Open (Needs Design)
**Found:** 2026-01-11
**Source:** `docs/_debt/friction.md` - Items requiring brainstorming before implementation

---

## Summary

After addressing BUG-047, SPEC-035, SPEC-036, and other concrete fixes, several friction items remain that are
**design problems** rather than bugs. These require architectural decisions before implementation.

---

## Residual Items

### 1. Data Sync Sports Domination (CLI Gap)

**Problem:** `kalshi data sync-markets` doesn't expose `--mve-filter` flag, so default syncs are dominated by
Sports multivariate parlays (~95% of first pages).

**Current state:**
- API client supports `mve_filter` parameter ✅
- `scan opportunities` has `--no-sports` ✅
- `market list` has `--exclude-category Sports` ✅
- `data sync-markets` has NO filtering ❌

**Design question:** Should `sync-markets` default to excluding MVE, or require explicit `--mve-filter exclude`?

**Effort:** Small (wire existing parameter to CLI flag)

---

### 2. Exa Integration Gap (Research Pipeline Architecture)

**Problem:** Claude agents give "vibes-based" recommendations from training data instead of grounded research.

**Current state:**
- Exa CLI commands exist (`kalshi research context`, `kalshi news collect`)
- But agents don't automatically use them before making recommendations
- No forcing function for research-before-recommendation

**Design questions:**
1. Should Exa be called automatically for any market analysis?
2. Should there be a "pre-flight checklist" prompt engineering pattern?
3. Should there be a dedicated Research Agent that handles search + summarization?
4. Should Exa be exposed via MCP for any agent harness to use natively?

**From friction.md:**
> "The friction is NOT in the Kalshi API integration (that works well). The friction is in the
> **research → synthesis → structured output** pipeline."

**Effort:** Large (architectural decision + implementation)

---

### 3. Adversarial Research Pattern (Agent Safety)

**Problem:** When asked "Is X a good bet?", agents only research the bull case, creating confirmation bias.

**Lesson from Indiana bet ($17.76 loss):**
- Agent surfaced Indiana spread as "upside bet"
- Failed to surface: Indiana was undefeated, Oregon's recent performance
- No adversarial check was performed

**Design questions:**
1. Should every thesis require both `bull_case` AND `bear_case` populated?
2. Should there be a dedicated Adversarial Agent that argues AGAINST every recommendation?
3. Should there be a "basic facts gate" - surface 3-5 key facts before any recommendation?
4. Should agents refuse to recommend on domains with stale training data (sports, breaking news)?

**From friction.md:**
> "FORCE both bull AND bear research on EVERY recommendation"

**Effort:** Medium (prompt engineering + possibly new agent role)

---

### 4. New Market Alert System (Information Arbitrage)

**Problem:** Best edge exists on newly opened markets where crowd hasn't priced in information yet.

**Current state:**
- No alerting for new markets
- No quick research pipeline for new opportunities

**Proposed feature:**
```bash
# Scan for new markets with quick research
kalshi scan new-markets --hours 24 --categories politics,ai,tech --research
```

**Design questions:**
1. How to detect "new" markets (created_time field)?
2. Should this auto-trigger Exa research?
3. What's the signal-to-noise threshold?

**Effort:** Medium (new scan filter + optional Exa integration)

---

### 5. Missing `/series` Endpoint (Proper Category SSOT)

**Problem:** Current category filtering uses `/events` which works but isn't Kalshi's intended pattern.

**From hacks.md:**
> "Kalshi's Intended Pattern:
> GET /search/tags_by_categories  # Discover available categories
> GET /series?category=Politics   # Get series in that category
> GET /markets?series_ticker=...  # Get markets for those series"

**Current state:**
- We use `/events` + `Event.category` (works but deprecated)
- `/series` endpoint not implemented in our client
- `/search/tags_by_categories` not implemented

**Design questions:**
1. Is this worth implementing now, or wait until Kalshi removes `Event.category`?
2. Should we implement as future-proofing or as response to deprecation?

**Effort:** Medium (new API methods + migration of category logic)

---

### 6. Jan 15, 2026 Deprecation Cleanup (Scheduled)

**Problem:** Kalshi removing cent-denominated fields on Jan 15, 2026.

**From backwards-compatibility.md:**
- Market model: `yes_bid`, `yes_ask`, `no_bid`, `no_ask`, `last_price`, `liquidity`
- Orderbook model: `yes`, `no` (cents format)
- Candlestick model: cent fields

**Design questions:**
1. Remove fields entirely or keep as optional?
2. Simplify computed properties or keep fallback logic?

**Effort:** Small (cleanup after date passes)

**Action:** Create calendar reminder for Jan 16, 2026

---

## Priority Matrix

| Item | Impact | Effort | Priority |
|------|--------|--------|----------|
| Data sync mve-filter | Low | Small | P3 |
| Exa research pipeline | High | Large | P1 |
| Adversarial research | High | Medium | P1 |
| New market alerts | Medium | Medium | P2 |
| `/series` endpoint | Low | Medium | P3 |
| Jan 15 cleanup | Medium | Small | P2 (scheduled) |

---

## Next Steps

1. **Decide on research pipeline architecture** (Item 2) - This blocks Items 3 and 4
2. **Add `--mve-filter` to sync-markets** (Item 1) - Quick win, can do anytime
3. **Wait for Jan 15** (Item 6) - Scheduled cleanup
4. **Monitor `Event.category` deprecation** (Item 5) - React when needed

---

## References

- `docs/_debt/friction.md` - Original friction log
- `hacks.md` - Missing API features and workarounds
- `backwards-compatibility.md` - Deprecation inventory
- `docs/_archive/debt/DEBT-013-category-filtering-events-ssot.md` - Related fix
