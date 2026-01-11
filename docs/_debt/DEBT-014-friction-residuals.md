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

**Code locations verified:**

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

| Item | Risk | Reason |
|------|------|--------|
| A1 | 🟢 Safe | Format was never used (greenfield project) |
| A2 | 🟢 Safe | OpenAPI confirms `market_positions` is correct |
| A3 | 🟡 Medium | Fallback may be needed for historical data |
| A4 | 🟡 Medium | WebSocket spec not documented, verify empirically |
| A5 | 🟢 Safe | Additive change (wiring existing parameter) |
| A6 | 🟢 Safe | Comment-only change (clarifies intent) |

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

**✅ VERIFIED (2026-01-11):** Kalshi OpenAPI spec confirms response field is `market_positions`.
The `positions` fallback is unnecessary.

**Verification steps before removal:**

1. [x] Check Kalshi OpenAPI spec → Confirmed: `GetPositionsResponse` uses `market_positions`
2. [ ] Add temporary logging: `if "positions" in data: logger.warning("Legacy positions key found")`
3. [ ] Run `kalshi portfolio sync` several times over 1-2 days
4. [ ] If warning never triggers, safe to remove

**Fix:** Remove `or data.get("positions")` fallback.

**Rollback:** If Kalshi ever returns `positions` key, re-add the fallback.

**Effort:** 15 minutes (verify + remove)

---

### A3. Settlement Time Fallback [P2] - VERIFY BEFORE REMOVE

**Source:** `backwards-compatibility.md` Category 2.3
**Location:** `src/kalshi_research/data/fetcher.py:138`

**Problem:**
```python
settled_at = api_market.settlement_ts or api_market.expiration_time
```

**Why it's debt:** Fallback for "historical data" that may not exist.

**⚠️ CAUTION (2026-01-11):** This fallback may be LEGITIMATELY NEEDED.

Kalshi OpenAPI spec says:
> `settlement_ts`: "Timestamp when the market was settled. Only filled for settled markets."
> Type: `string | null` (nullable)

The fallback exists because:
1. `settlement_ts` field was added Dec 19, 2025
2. Historical data synced before that date won't have `settlement_ts`
3. Function only runs for settled markets (`if not api_market.result: return None`)

**Verification steps before removal:**

1. [ ] Query local DB: `SELECT COUNT(*) FROM settlements WHERE settled_at IS NULL`
2. [ ] Check if any settlements use `expiration_time` instead of `settlement_ts`
3. [ ] If ALL settlements have proper `settlement_ts`, then safe to remove
4. [ ] If some are missing, the fallback is NEEDED - do NOT remove

**Fix (conditional):** Only remove if verification confirms no historical data needs the fallback.

**Rollback:** Re-add fallback if any settlement timestamps become NULL.

**Risk level:** 🟡 Medium - verify carefully before removal

**Effort:** 20 minutes (query + verify + conditional remove)

---

### A4. WebSocket Channel Fallback [P2] - VERIFY & REMOVE

**Source:** `backwards-compatibility.md` Category 2.4
**Location:** `src/kalshi_research/api/websocket/client.py:222`

**Problem:**
```python
channel = data.get("type") or data.get("channel")
```

**Why it's debt:** Unclear which key Kalshi uses. Creates ambiguity.

**⚠️ NOTE (2026-01-11):** WebSocket API is NOT in OpenAPI spec. Need separate verification.

**Verification steps before removal:**

1. [ ] Check Kalshi WebSocket docs: https://docs.kalshi.com/websocket
2. [ ] Add temporary logging: `logger.debug(f"WS message keys: {data.keys()}")`
3. [ ] Run `kalshi alerts monitor` and observe actual message structure
4. [ ] Confirm whether messages use `type` or `channel` key
5. [ ] If always `type`, safe to remove `or data.get("channel")`

**Fix:** Remove `or data.get("channel")` fallback after verification.

**Rollback:** If Kalshi ever sends `channel` key, re-add the fallback.

**Risk level:** 🟡 Medium - WebSocket not documented in OpenAPI, verify empirically

**Effort:** 20 minutes (check docs + observe + remove)

---

### A5. Data Sync MVE Filter [P3] - WIRE EXISTING PARAM

**Source:** `friction.md` - "Database Sync Sports Dominated"

**Problem:** `kalshi data sync-markets` doesn't expose `--mve-filter` flag.

**Current state:**
- API client supports `mve_filter` parameter ✅
- `DataFetcher.sync_markets()` does not pass `mve_filter` through ❌
- CLI doesn't expose it ❌

**Fix:** Plumb `mve_filter` end-to-end:
1. Add optional `mve_filter` param to `DataFetcher.sync_markets()`
2. Thread it into `self.client.get_all_markets(..., mve_filter=mve_filter)`
3. Add `--mve-filter` option to `kalshi data sync-markets` that passes through

**Effort:** 30 minutes

---

### A6. Clarify "DB Stores Cents" Comment [P3] - RENAME COMMENT

**Source:** `backwards-compatibility.md` Category 3.1
**Location:** `src/kalshi_research/data/fetcher.py:112-113`

**Problem:** The snapshot conversion comment says:

> "Database continues to store cents for backwards compatibility."

This is misleading. Storing cents is primarily a **precision** decision (avoid float issues), not a
compatibility layer.

**Fix:** Update the comment to say we store cents for precision / integer math.

**Effort:** 10 minutes

---

## Section B: Needs Design Decisions

> **User Decision (2026-01-11):**
> - B1: Yes, always research first (auto-research before recommendations)
> - B2: Yes, always show both sides (bull AND bear case required)
> - B3: Yes, alert on new markets
>
> **Status:** B1 and B2 are **BLOCKED BY FUTURE-001** implementation. The design is already
> specified in `docs/_future/FUTURE-001-exa-research-agent.md`. When FUTURE-001 is implemented,
> B1 and B2 become default behavior.

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

**Status:** 📋 **NEEDS SPEC** (not covered by FUTURE-001)

**Problem:** Best edge exists on newly opened markets where crowd hasn't priced in information yet.

**Design decision:** Yes, alert on new markets matching user interests (politics, AI, tech).

**Current state:**
- No alerting for new markets
- No quick research pipeline for new opportunities

**Proposed feature:**
```bash
# Scan for new markets with quick research
kalshi scan new-markets --hours 24 --categories politics,ai,tech --research
```

**Design questions:**
1. How to detect "new" markets (`created_time` field)?
2. Should this auto-trigger Exa research?
3. What's the signal-to-noise threshold?

**✅ INVESTIGATED (2026-01-11): Liquidity Filtering Analysis**

**Finding 1: Default filters are permissive**

| Filter | Default | Impact on New Markets |
|--------|---------|----------------------|
| `--min-volume` | 0 | No exclusion |
| `--max-spread` | 100¢ | No exclusion (max range) |
| `--min-liquidity` | None | Off by default |

**Finding 2: The REAL filter is in `scanner.py:220-224`**

```python
# SKIP: Unpriced markets (0/0 or 0/100 placeholder quotes)
if m.yes_bid_cents == 0 and m.yes_ask_cents == 0:
    continue  # No quotes at all
if m.yes_bid_cents == 0 and m.yes_ask_cents == 100:
    continue  # Placeholder: no real price discovery
```

New markets with NO price discovery (bid=0, ask=100) ARE skipped. This is technically correct
(can't analyze markets with no prices), but misses the "information arbitrage window."

**Finding 3: `created_time` field EXISTS** (`api/models/market.py:84`)

We CAN detect new markets. The Market model already has this field.

**Recommended B3 implementation:**

```bash
# Proposed new command/filter
kalshi scan new-markets --hours 24 --include-unpriced --categories politics,ai,tech
```

Options to address:

1. `--include-unpriced` flag to show markets even without real price discovery
2. Label unpriced markets as "NEW (awaiting price discovery)" in results
3. Different threshold defaults for new market scanning

**Effort:** Medium (new scan filter + optional Exa integration)

**Next step:** Create SPEC-037 for new market alerts with appropriate filter logic

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
| A6 | Clarify DB cents comment | Low | 10 min | P3 | Can fix NOW |
| B1 | Exa research pipeline | High | Large | P1 | ⏸️ Blocked (FUTURE-001) |
| B2 | Adversarial research | High | Medium | P1 | ⏸️ Blocked (FUTURE-001) |
| B3 | New market alerts | Medium | Medium | P2 | 📋 Needs spec |
| C1 | `/series` endpoint | Low | Medium | P3 | Blocked |
| C2 | Jan 15 cleanup | Medium | Small | P2 | Scheduled |

---

## Next Steps

### Immediate (Can do now)
1. **A1**: Delete thesis legacy dict format (~10 min)
2. **A2-A4**: Verify and remove fallbacks (~45 min total)
3. **A5**: Wire `--mve-filter` to sync-markets (~30 min)
4. **A6**: Clarify DB cents storage comment (~10 min)

### Blocked (Waiting on FUTURE-001)
4. **B1**: Implement `ResearchAgent` from FUTURE-001 spec
5. **B2**: Included in FUTURE-001 (bull/bear case generation)

### Needs Spec
6. **B3**: Create SPEC-0XX for new market alerts (see liquidity concern below)

### Scheduled
7. **C2**: Wait for Jan 15, 2026, then cleanup
8. **C1**: React when Kalshi removes `Event.category`

---

## Cross-References

| Document | Purpose | Relationship |
|----------|---------|--------------|
| `docs/_archive/debt/friction.md` | Original friction log | Source (archived 2026-01-11) |
| `docs/_archive/debt/hacks.md` | Hacky implementations | Source (archived 2026-01-11) |
| `docs/_archive/debt/backwards-compatibility.md` | Compat code inventory | Source (archived 2026-01-11) |
| `docs/_future/FUTURE-001-exa-research-agent.md` | Exa agent spec | **Blocks B1/B2** |
| `docs/_future/TODO-00A-api-verification-post-deadline.md` | Jan 15 verification | Related to C2 |
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
> - B3: Alert on new markets → NEEDS SPEC (see investigation below)
>
> **✅ RESOLVED (B3 Liquidity Concern):**
> Investigated on 2026-01-11. See B3 section for full findings. Summary:
> - Default filters are permissive (`--min-volume=0`, `--max-spread=100`)
> - The REAL filter is unpriced markets (bid=0, ask=100) being skipped in scanner.py:220-224
> - `created_time` field EXISTS on Market model - we CAN detect new markets
> - **Next step:** Create SPEC-037 with `--include-unpriced` flag option
>
> **Review checklist:**
> - [x] Search `scan opportunities` for volume/liquidity filters ✅ Done (see B3)
> - [x] Check if `created_time` field is available on Market model ✅ Yes (`market.py:84`)
> - [ ] Verify Section A items (A1-A6) are still accurate (last verified: 2026-01-11)
> - [ ] Check if Jan 15, 2026 has passed (C2 trigger)
>
> **If you're reading this post-compaction:** Re-read this document and FUTURE-001 before
> implementing anything. The design decisions are already made.
