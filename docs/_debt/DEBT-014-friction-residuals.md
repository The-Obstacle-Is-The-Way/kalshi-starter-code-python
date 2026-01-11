# DEBT-014: Technical Debt Consolidation

**Priority:** Mixed (P0-P3)
**Status:** Open
**Found:** 2026-01-11
**Sources:**
- `docs/_debt/friction.md` - User friction items
- `docs/_debt/hacks.md` - Hacky implementations and missing APIs
- `docs/_debt/backwards-compatibility.md` - Unnecessary compat code

---

## Summary

This document consolidates ALL actionable technical debt from friction.md, hacks.md, and
backwards-compatibility.md into a single source of truth.

**Categories:**
- **Section A**: Can fix NOW (no blockers)
- **Section B**: Needs design decisions
- **Section C**: Blocked/Scheduled (external dependencies)

---

## Section A: Can Fix NOW (No Blockers)

### A1. Thesis Legacy Dict Format [P0] - DELETE NOW

**Source:** `backwards-compatibility.md` Category 2.1
**Location:** `src/kalshi_research/research/thesis.py:324`

**Problem:** Legacy dict format parsing exists for a format that was never used in production.

```python
# Legacy dict format: {"<id>": {...}, ...}
```

**Why it's debt:** ~20 lines of parsing code for hypothetical migration. Greenfield project = no users.

**Fix:** Delete the legacy parsing code block entirely.

**Effort:** 10 minutes

---

### A2. Portfolio Positions Fallback [P2] - VERIFY & REMOVE

**Source:** `backwards-compatibility.md` Category 2.2, `hacks.md` 2.3
**Location:** `src/kalshi_research/api/client.py:582`

**Problem:**
```python
raw = data.get("market_positions") or data.get("positions") or []
```

**Why it's debt:** Fallback to `positions` based on "older docs" - may never trigger.

**Fix:**
1. Verify Kalshi OpenAPI spec uses `market_positions`
2. If confirmed, remove `or data.get("positions")` fallback

**Effort:** 15 minutes (verify + remove)

---

### A3. Settlement Time Fallback [P2] - VERIFY & REMOVE

**Source:** `backwards-compatibility.md` Category 2.3
**Location:** `src/kalshi_research/data/fetcher.py:138`

**Problem:**
```python
settled_at = api_market.settlement_ts or api_market.expiration_time
```

**Why it's debt:** Fallback for "historical data" that may not exist.

**Fix:**
1. Check if any historical data uses expiration_time instead of settlement_ts
2. If none, remove fallback

**Effort:** 15 minutes

---

### A4. WebSocket Channel Fallback [P2] - VERIFY & REMOVE

**Source:** `backwards-compatibility.md` Category 2.4
**Location:** `src/kalshi_research/api/websocket/client.py:222`

**Problem:**
```python
channel = data.get("type") or data.get("channel")
```

**Why it's debt:** Unclear which key Kalshi uses. Creates ambiguity.

**Fix:**
1. Verify Kalshi WebSocket spec uses `type`
2. If confirmed, remove `or data.get("channel")` fallback

**Effort:** 15 minutes

---

### A5. Data Sync MVE Filter [P3] - WIRE EXISTING PARAM

**Source:** `friction.md` - "Database Sync Sports Dominated"

**Problem:** `kalshi data sync-markets` doesn't expose `--mve-filter` flag.

**Current state:**
- API client supports `mve_filter` parameter ✅
- CLI doesn't expose it ❌

**Fix:** Add `--mve-filter` option to `data sync-markets` command.

**Effort:** 30 minutes

---

## Section B: Needs Design Decisions

### B1. Exa Integration Gap (Research Pipeline Architecture)

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

### B2. Adversarial Research Pattern (Agent Safety)

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

### B3. New Market Alert System (Information Arbitrage)

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

## Section C: Blocked/Scheduled (External Dependencies)

### C1. Missing `/series` Endpoint (Proper Category SSOT)

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

**Blocked by:** Wait until Kalshi removes `Event.category` field

**Related items (blocked by this):**
- Category ticker prefix mapping (`hacks.md` 3.1)
- Missing `/search/tags_by_categories` (`hacks.md` 1.2)
- Missing `/search/filters_by_sport` (`hacks.md` 1.3)

---

### C2. Jan 15, 2026 Deprecation Cleanup (Scheduled)

**Problem:** Kalshi removing cent-denominated fields on Jan 15, 2026.

**From backwards-compatibility.md:**
- Market model: `yes_bid`, `yes_ask`, `no_bid`, `no_ask`, `last_price`, `liquidity`
- Orderbook model: `yes`, `no` (cents format)
- Candlestick model: cent fields

**Design questions:**
1. Remove fields entirely or keep as optional?
2. Simplify computed properties or keep fallback logic?

**Effort:** Small (cleanup after date passes)

**Blocked by:** Wait until Jan 15, 2026

**Cross-reference:** See `docs/_future/TODO-00A-api-verification-post-deadline.md`

---

## Priority Matrix

| ID | Item | Impact | Effort | Priority | Status |
|----|------|--------|--------|----------|--------|
| A1 | Thesis legacy dict format | Low | 10 min | **P0** | Can fix NOW |
| A2 | Portfolio positions fallback | Low | 15 min | P2 | Can fix NOW |
| A3 | Settlement time fallback | Low | 15 min | P2 | Can fix NOW |
| A4 | WebSocket channel fallback | Low | 15 min | P2 | Can fix NOW |
| A5 | Data sync mve-filter | Low | 30 min | P3 | Can fix NOW |
| B1 | Exa research pipeline | High | Large | P1 | Needs design |
| B2 | Adversarial research | High | Medium | P1 | Needs design |
| B3 | New market alerts | Medium | Medium | P2 | Needs design |
| C1 | `/series` endpoint | Low | Medium | P3 | Blocked |
| C2 | Jan 15 cleanup | Medium | Small | P2 | Scheduled |

---

## Next Steps

### Immediate (Can do now)
1. **A1**: Delete thesis legacy dict format (~10 min)
2. **A2-A4**: Verify and remove fallbacks (~45 min total)
3. **A5**: Wire `--mve-filter` to sync-markets (~30 min)

### Design Required
4. **B1**: Decide on Exa research pipeline architecture (see `FUTURE-001`)
5. **B2-B3**: Design depends on B1

### Scheduled
6. **C2**: Wait for Jan 15, 2026, then cleanup
7. **C1**: React when Kalshi removes `Event.category`

---

## Cross-References

| Document | Purpose | Relationship |
|----------|---------|--------------|
| `docs/_debt/friction.md` | Original friction log | Source (historical) |
| `docs/_debt/hacks.md` | Hacky implementations | Source (audit findings) |
| `docs/_debt/backwards-compatibility.md` | Compat code inventory | Source (audit findings) |
| `docs/_future/FUTURE-001-exa-research-agent.md` | Exa agent spec | Blocks B1 design |
| `docs/_future/TODO-00A-api-verification-post-deadline.md` | Jan 15 verification | Related to C2 |
| `docs/_future/TODO-00B-trade-executor-phase2.md` | TradeExecutor | Separate track |
