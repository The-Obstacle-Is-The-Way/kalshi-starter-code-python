# DEBT-014: Technical Debt Consolidation

**Priority:** Mixed (P0-P3)
**Status:** Open
**Found:** 2026-01-11
**Sources:** (archived 2026-01-11)
- `docs/_archive/debt/friction.md` - User friction items
- `docs/_archive/debt/hacks.md` - Hacky implementations and missing APIs
- `docs/_archive/debt/backwards-compatibility.md` - Unnecessary compat code

---

## Summary

This document consolidates ALL actionable technical debt from friction.md, hacks.md, and
backwards-compatibility.md into a single source of truth.

**Categories:**
- **Section A**: Can fix NOW (no blockers)
- **Section B**: Needs design decisions
- **Section C**: Blocked/Scheduled (external dependencies)

---

## Audit Log (2026-01-11)

**Pre-fix code locations verified (before Section A changes):**

| Item | Location | Verified |
|------|----------|----------|
| A1 | `thesis.py:324-342` | ✅ Legacy dict parsing exists |
| A2 | `client.py:582` | ✅ `data.get("market_positions") or data.get("positions")` exists |
| A3 | `fetcher.py:138` | ✅ `settlement_ts or expiration_time` exists |
| A4 | `websocket/client.py:222` | ✅ `data.get("type") or data.get("channel")` exists |
| A5 | `cli/data.py:140-178` | ✅ `sync-markets` command lacks `--mve-filter` |
| A6 | `fetcher.py:112-113` | ✅ Snapshot comment frames cents as "backwards compatibility" |

**API verification (Kalshi OpenAPI spec):**

| Item | Finding |
|------|---------|
| A2 | ✅ Confirmed: `GetPositionsResponse` uses `market_positions` (not `positions`) |
| A3 | ⚠️ `settlement_ts` is nullable, only filled for settled markets - fallback may be needed |
| A4 | ❓ WebSocket not in OpenAPI spec - needs empirical verification |

**Risk assessment:**

| Item | Risk | Status |
|------|------|--------|
| A1 | 🟢 Safe | ✅ COMPLETED (2026-01-11) |
| A2 | 🟢 Safe | ✅ COMPLETED (2026-01-11) |
| A3 | ⬜ N/A | ✅ VERIFIED CORRECT (2026-01-11) - NOT debt, keep as-is |
| A4 | 🟢 Safe | ✅ COMPLETED (2026-01-11) - Verified via Kalshi docs |
| A5 | 🟢 Safe | ✅ COMPLETED (2026-01-11) |
| A6 | 🟢 Safe | ✅ COMPLETED (2026-01-11) |

---

## Section A: Can Fix NOW (No Blockers)

### A1. Thesis Legacy Dict Format [P0] - ✅ COMPLETED

**Source:** `backwards-compatibility.md` Category 2.1
**Location:** `src/kalshi_research/research/thesis.py:324`

**Problem:** Legacy dict format parsing exists for a format that was never used in production.

**Status:** ✅ **COMPLETED** (2026-01-11, commit 12657bb)
- Verified `data/theses.json` uses new `{"theses": [...]}` format
- Deleted ~20 lines of legacy dict parsing code
- Simplified error message for unknown schema

**Effort:** 10 minutes

---

### A2. Portfolio Positions Fallback [P2] - ✅ COMPLETED

**Source:** `backwards-compatibility.md` Category 2.2, `hacks.md` 2.3
**Location:** `src/kalshi_research/api/client.py:581`

**Problem:**
```python
raw = data.get("market_positions") or data.get("positions") or []
```

**Why it's debt:** Fallback to `positions` based on "older docs" - may never trigger.

**Status:** ✅ **COMPLETED** (2026-01-11, commit 12657bb)
- Verified Kalshi OpenAPI spec uses `market_positions`
- Removed `or data.get("positions")` fallback
- Updated test to verify new behavior (returns empty for legacy key)

**Rollback:** If Kalshi ever returns `positions` key, re-add the fallback.

**Effort:** 15 minutes

---

### A3. Settlement Time Fallback [P2] - ✅ VERIFIED CORRECT (NOT DEBT)

**Source:** `backwards-compatibility.md` Category 2.3
**Location:** `src/kalshi_research/data/fetcher.py:138`

**Code:**
```python
settled_at = api_market.settlement_ts or api_market.expiration_time
```

**Status:** ✅ **VERIFIED CORRECT** (2026-01-11) - This is NOT debt, it's correct behavior.

**Verification performed:**

1. Kalshi OpenAPI spec confirms `settlement_ts` is nullable: `string | null`
2. Test `test_api_market_to_settlement_falls_back_to_expiration_time` explicitly verifies fallback
3. The fallback handles unsettled markets correctly

**Why this is CORRECT behavior (not debt):**

- `settlement_ts` is only filled for settled markets per Kalshi API spec
- For active/unsettled markets, `settlement_ts` is `null`
- The fallback to `expiration_time` is the documented proxy
- Removing the fallback would break the function for null settlement timestamps

**Conclusion:** Keep this code as-is. No action required.

---

### A4. WebSocket Channel Fallback [P2] - ✅ COMPLETED

**Source:** `backwards-compatibility.md` Category 2.4
**Location:** `src/kalshi_research/api/websocket/client.py:222`

**Problem:**
```python
channel = data.get("type") or data.get("channel")
```

**Why it was debt:** Unclear which key Kalshi uses. Created ambiguity.

**Status:** ✅ **COMPLETED** (2026-01-11, commit 2dc41ba)

**Verification performed:**

1. [x] Checked [Kalshi WebSocket docs](https://docs.kalshi.com/websockets/)
2. [x] Verified message structures for all channel types:
   - `orderbook_snapshot` / `orderbook_delta` → uses `"type"`
   - `ticker` → uses `"type"`
   - `trade` → uses `"type"`
   - Control messages (subscribed, error, ok) → uses `"type"`
3. [x] Confirmed existing test `test_message_routing` uses `"type": "ticker"`
4. [x] Removed `or data.get("channel")` fallback
5. [x] All WebSocket tests pass (5/5)

**Fix applied:**
```python
# Before
channel = data.get("type") or data.get("channel")

# After
channel = data.get("type")
```

Added documentation reference comment in code.

**Rollback:** If Kalshi ever changes to `channel` key, re-add the fallback.

---

### A5. Data Sync MVE Filter (Multivariate Events) [P3] - ✅ COMPLETED

**Source:** `friction.md` - "Database Sync Sports Dominated"

**Problem:** `kalshi data sync-markets` doesn't expose `--mve-filter` flag (MVE = multivariate events).

**Status:** ✅ **COMPLETED** (2026-01-11, commit 12657bb)
- Added `mve_filter` parameter to `DataFetcher.sync_markets()`
- Passed through to `self.client.get_all_markets(..., mve_filter=...)`
- Added `--mve-filter` CLI option to `kalshi data sync-markets`
- Usage: `kalshi data sync-markets --mve-filter exclude` (skip sports parlays)

**Effort:** 30 minutes

---

### A6. Clarify "DB Stores Cents" Comment [P3] - ✅ COMPLETED

**Source:** `backwards-compatibility.md` Category 3.1
**Location:** `src/kalshi_research/data/fetcher.py:112-113`

**Problem:** The snapshot conversion comment said:

> "Database continues to store cents for backwards compatibility."

This was misleading. Storing cents is primarily a **precision** decision (avoid float issues), not a
compatibility layer.

**Status:** ✅ **COMPLETED** (2026-01-11, commit ad3ab73)
- Updated comment to: "Database stores cents (integers) for precision - avoids floating-point rounding issues."

**Effort:** 5 minutes

---

## Section B: Needs Design Decisions

### User Decisions (2026-01-11)

- B1: Yes, always research first (auto-research before recommendations)
- B2: Yes, always show both sides (bull AND bear case required)
- B3: Yes, alert on new markets

**Status:** B1 and B2 are **BLOCKED BY FUTURE-001** implementation. The design is already specified in
`docs/_future/FUTURE-001-exa-research-agent.md`. When FUTURE-001 is implemented, B1 and B2 become
default behavior.

### B1. Exa Integration Gap (Research Pipeline Architecture)

**Status:** ⏸️ **BLOCKED BY FUTURE-001**

**Problem:** Claude agents give "vibes-based" recommendations from training data instead of grounded research.

**Current state:**
- Exa CLI commands exist (`kalshi research context`, `kalshi news collect`)
- But agents don't automatically use them before making recommendations
- No forcing function for research-before-recommendation

**Design decision:** Auto-research ALWAYS before recommendations.

**Implementation:** See `docs/_future/FUTURE-001-exa-research-agent.md` - the `ResearchAgent` class
already specifies this behavior with budget controls and depth levels.

**Effort:** Large (implement FUTURE-001)

---

### B2. Adversarial Research Pattern (Agent Safety)

**Status:** ⏸️ **BLOCKED BY FUTURE-001**

**Problem:** When asked "Is X a good bet?", agents only research the bull case, creating confirmation bias.

**Lesson from Indiana bet ($17.76 loss):**
- Agent surfaced Indiana spread as "upside bet"
- Failed to surface: Indiana was undefeated, Oregon's recent performance
- No adversarial check was performed

**Design decision:** ALWAYS show both sides (bull_case AND bear_case required).

**Implementation:** Already specified in FUTURE-001. The `ResearchResult` dataclass includes both
`bull_case` and `bear_case` fields. The `ResearchAgent._generate_cases()` method explicitly
searches for both bullish AND bearish signals.

**Effort:** Included in FUTURE-001 implementation

---

### B3. New Market Alert System (Information Arbitrage)

**Status:** ✅ **IMPLEMENTED (Phase 1)** → See [SPEC-039](../_specs/SPEC-039-new-market-alerts.md)

**Problem:** Best edge exists on newly opened markets where crowd hasn't priced in information yet.

**Design decision:** Yes, alert on new markets matching user interests (politics, AI, tech).

**Current state:**
- ✅ Phase 1 implemented: `kalshi scan new-markets` (info-arbitrage window scanner)
- ⏸️ Phase 2 optional: `--research` (Exa quick context) not implemented yet

**Phase 2 (optional):**
```bash
# Scan for new markets with quick research
kalshi scan new-markets --hours 24 --category politics,ai,tech --research
```

**Design questions:**
1. How to detect "new" markets (`created_time` field)?
2. Should this auto-trigger Exa research?
3. What's the signal-to-noise threshold?

#### ✅ INVESTIGATED (2026-01-11): Liquidity Filtering Analysis

#### Finding 1: Default filters are permissive

| Filter | Default | Impact on New Markets |
|--------|---------|----------------------|
| `--min-volume` | 0 | No exclusion |
| `--max-spread` | 100¢ | No exclusion (max range) |
| `--min-liquidity` | None | Off by default |

#### Finding 2: The REAL filter is in `scanner.py:220-224`

```python
# SKIP: Unpriced markets (0/0 or 0/100 placeholder quotes)
if m.yes_bid_cents == 0 and m.yes_ask_cents == 0:
    continue  # No quotes at all
if m.yes_bid_cents == 0 and m.yes_ask_cents == 100:
    continue  # Placeholder: no real price discovery
```

New markets with NO price discovery (bid=0, ask=100) ARE skipped. This is technically correct
(can't analyze markets with no prices), but misses the "information arbitrage window."

#### Finding 3: `created_time` field EXISTS (`api/models/market.py:137`)

We CAN detect new markets. The Market model already has this field.

**Recommended B3 implementation:**

```bash
# Proposed new command/filter
kalshi scan new-markets --hours 24 --include-unpriced --category politics,ai,tech
```

Options to address:

1. `--include-unpriced` flag to show markets even without real price discovery
2. Label unpriced markets clearly (e.g., `[AWAITING PRICE DISCOVERY]`, `[NO QUOTES]`)
3. Different threshold defaults for new market scanning

**Effort:** Medium (new scan filter + optional Exa integration)

**Next step (optional):** Implement SPEC-039 Phase 2 (`--research` Exa integration)

---

## Section C: Blocked/Scheduled (External Dependencies)

### C1. Missing `/series` Endpoint (Proper Category SSOT) - ✅ RESOLVED

**Status:** ✅ **RESOLVED** (2026-01-12, SPEC-037)

**Problem:** Current category filtering uses `/events` which works but isn't Kalshi's intended pattern.

**From hacks.md:**
> "Kalshi's Intended Pattern:
> GET /search/tags_by_categories  # Discover available categories
> GET /series?category=Politics   # Get series in that category
> GET /markets?series_ticker=...  # Get markets for those series"

**Resolution:**
SPEC-037 implemented the series discovery endpoints:
- ✅ `GET /series` → `get_series_list()` in `src/kalshi_research/api/client.py`
- ✅ `GET /series/{ticker}` → `get_series()` in `src/kalshi_research/api/client.py`
- ✅ `GET /search/tags_by_categories` → `get_tags_by_categories()` in `src/kalshi_research/api/client.py`
- ✅ Golden fixtures: `series_list_response.json`, `series_single_response.json`, `tags_by_categories_response.json`

**Remaining work:**
- Migrate CLI commands to use series-first pattern (optional, `/events` still works)
- `GET /search/filters_by_sport` (P3, sports-specific)

---

### C2. Jan 15, 2026 Deprecation Cleanup (Post-deadline)

**Problem:** Kalshi removing cent-denominated fields on Jan 15, 2026.

**From backwards-compatibility.md:**
- Market model: `yes_bid`, `yes_ask`, `no_bid`, `no_ask`, `last_price`, `liquidity`
- Orderbook model: `yes`, `no` (cents format)
- Candlestick model: cent fields

**Design questions:**
1. Remove fields entirely or keep as optional?
2. Simplify computed properties or keep fallback logic?

**Effort:** Small (cleanup after date passes)

**Status:** Jan 15, 2026 has passed. Re-evaluate and cleanup if still needed.

**Cross-reference:** See `docs/_archive/future/TODO-00A-api-verification-post-deadline.md`

---

## Priority Matrix

| ID | Item | Impact | Effort | Priority | Status |
|----|------|--------|--------|----------|--------|
| A1 | Thesis legacy dict format | Low | 10 min | **P0** | ✅ COMPLETED |
| A2 | Portfolio positions fallback | Low | 15 min | P2 | ✅ COMPLETED |
| A3 | Settlement time fallback | N/A | N/A | N/A | ✅ VERIFIED CORRECT (not debt) |
| A4 | WebSocket channel fallback | Low | 15 min | P2 | ✅ COMPLETED |
| A5 | Data sync mve-filter | Low | 30 min | P3 | ✅ COMPLETED |
| A6 | Clarify DB cents comment | Low | 5 min | P3 | ✅ COMPLETED |
| B1 | Exa research pipeline | High | Large | P1 | ⏸️ Blocked (FUTURE-001) |
| B2 | Adversarial research | High | Medium | P1 | ⏸️ Blocked (FUTURE-001) |
| B3 | New market alerts | Medium | Medium | P2 | ✅ Implemented (SPEC-039 Phase 1) |
| C1 | `/series` endpoint | Low | Medium | P3 | ✅ RESOLVED (SPEC-037) |
| C2 | Jan 15 cleanup | Medium | Small | P2 | Unblocked (post-deadline) |

---

## Next Steps

### Section A Summary (2026-01-11)

| Item | Outcome |
|------|---------|
| A1 | ✅ DONE - Deleted legacy dict parsing |
| A2 | ✅ DONE - Removed positions fallback |
| A3 | ✅ CLOSED - Verified CORRECT (not debt) |
| A4 | ✅ DONE - Removed channel fallback (verified via Kalshi docs) |
| A5 | ✅ DONE - Added `--mve-filter` CLI option |
| A6 | ✅ DONE - Fixed misleading comment |

**🎉 SECTION A COMPLETE** - All items resolved (2026-01-11)

### Remaining Work

None for Section A.

### Blocked (Waiting on FUTURE-001)
2. **B1**: Implement `ResearchAgent` from FUTURE-001 spec
3. **B2**: Included in FUTURE-001 (bull/bear case generation)

### Ready for Implementation
4. **B3**: ✅ Implemented via SPEC-039 Phase 1 (`kalshi scan new-markets`)

### Scheduled
5. **C2**: Jan 15 has passed; re-evaluate and cleanup if still needed

### Recently Resolved
6. **C1**: ✅ RESOLVED (2026-01-12) - Series endpoints implemented via SPEC-037

---

## Cross-References

| Document | Purpose | Relationship |
|----------|---------|--------------|
| `docs/_archive/debt/friction.md` | Original friction log | Source (archived 2026-01-11) |
| `docs/_archive/debt/hacks.md` | Hacky implementations | Source (archived 2026-01-11) |
| `docs/_archive/debt/backwards-compatibility.md` | Compat code inventory | Source (archived 2026-01-11) |
| `docs/_future/FUTURE-001-exa-research-agent.md` | Exa agent spec | **Blocks B1/B2** |
| `docs/_archive/future/TODO-00A-api-verification-post-deadline.md` | Jan 15 verification | Related to C2 |
| `docs/_future/TODO-00B-trade-executor-phase2.md` | TradeExecutor | Separate track |

---

## Post-Compaction Review Notes (2026-01-11)

> **For future Claude sessions after context compaction:**
>
> This document was audited on 2026-01-11. All source documents (friction.md, hacks.md,
> backwards-compatibility.md) have been archived to `docs/_archive/debt/`.
>
> **Key decisions made:**
> - B1: Auto-research always → BLOCKED BY FUTURE-001
> - B2: Always show bull/bear → BLOCKED BY FUTURE-001
> - B3: Alert on new markets → SPECCED (SPEC-039)
>
> **✅ RESOLVED (B3 Liquidity Concern):**
> Investigated on 2026-01-11. See B3 section for full findings. Summary:
> - Default filters are permissive (`--min-volume=0`, `--max-spread=100`)
> - The REAL filter is unpriced markets (bid=0, ask=100) being skipped in scanner.py:220-224
> - `created_time` field EXISTS on Market model - we CAN detect new markets
> - ✅ Implemented: SPEC-039 Phase 1 (`kalshi scan new-markets` command)
>
> **Review checklist:**
> - [x] Search `scan opportunities` for volume/liquidity filters ✅ Done (see B3)
> - [x] Check if `created_time` field is available on Market model ✅ Yes (`market.py:84`)
> - [ ] Verify Section A items (A1-A6) are still accurate (last verified: 2026-01-11)
> - [x] Jan 15, 2026 has passed (C2 unblocked)
>
> **If you're reading this post-compaction:** Re-read this document and FUTURE-001 before
> implementing anything. The design decisions are already made.
