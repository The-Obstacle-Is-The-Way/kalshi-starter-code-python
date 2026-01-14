# SPEC-039: New Market Alerts (Information Arbitrage Window)

**Status:** Phase 1 ✅ (Phase 2 optional)
**Priority:** P2 (Trading Edge)
**Created:** 2026-01-13
**Owner:** Solo
**Effort:** ~1 day
**Source:** DEBT-014 B3

---

## Summary

Add a `kalshi scan new-markets` command to surface newly opened markets where information arbitrage
opportunities exist. The best edge often exists on markets before the crowd has priced in available
information.

This spec addresses DEBT-014 B3: "New Market Alert System (Information Arbitrage)".

---

## Goals

1. **Surface new markets** created within a configurable time window (default: 24h)
2. **Handle unpriced markets** that the current scanner skips (bid=0, ask=100)
3. **Optional Exa integration** for quick research on new opportunities
4. **Category filtering** to focus on user interests (politics, AI, tech, etc.)

---

## Non-Goals

- No real-time push notifications (polling/CLI only)
- No automated trading (research tool only)
- No changes to existing `scan opportunities` behavior (additive command)

---

## Current State (SSOT)

### Market model has `created_time`

```python
# src/kalshi_research/api/models/market.py:137
created_time: datetime | None = Field(default=None, description="When the market was created")
```

### Scanner skips unpriced markets

```python
# src/kalshi_research/analysis/scanner.py:220-224
# SKIP: Unpriced markets (0/0 or 0/100 placeholder quotes)
if m.yes_bid_cents == 0 and m.yes_ask_cents == 0:
    continue  # No quotes at all
if m.yes_bid_cents == 0 and m.yes_ask_cents == 100:
    continue  # Placeholder: no real price discovery
```

This is correct for the `opportunities` scanner (can't analyze markets with no prices), but misses
the "information arbitrage window" use case.

### Category filtering exists

```bash
# Already implemented via SPEC-036
kalshi scan opportunities --category politics
```

---

## Design

### 1) New command: `kalshi scan new-markets`

```bash
kalshi scan new-markets [OPTIONS]

Options:
  --hours INTEGER        Hours to look back for new markets (default: 24)
  --category TEXT        Filter by category (comma-separated; aliases supported)
  --categories TEXT      Alias for --category
  --include-unpriced     Include markets without real price discovery
  --limit INTEGER        Max results to show (default: 20)
  --max-pages INTEGER    Optional pagination safety limit (None = full)
  --json                 Output as JSON
  --full                 Disable truncation

Phase 2 (optional):
  --research             Run Exa research on each result (costs money)
```

### 2) Newness detection

Use `Market.created_time` as primary signal:

```python
def is_new_market(market: Market, hours: int = 24) -> bool:
    if market.created_time is None:
        # Fallback: use open_time as proxy (less accurate)
        reference_time = market.open_time
    else:
        reference_time = market.created_time

    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    return reference_time >= cutoff
```

### 3) Unpriced market handling

When `--include-unpriced` is set, show markets even if they have placeholder quotes:

| Pricing State | Default Behavior | With `--include-unpriced` |
|---------------|------------------|---------------------------|
| Real quotes (bid > 0, ask < 100) | ✅ Show | ✅ Show |
| No quotes (bid=0, ask=0) | ❌ Skip | ✅ Show with label |
| Placeholder (bid=0, ask=100) | ❌ Skip | ✅ Show with label |

Label format: `[AWAITING PRICE DISCOVERY]` or `[NO QUOTES]`

### 4) Output format

```text
New Markets (last 24 hours)

┌────────────────────┬─────────┬──────────────────────┬───────────┬──────────┬──────────┐
│ Ticker             │ Status  │ Title                 │ Yes       │ Category │ Created  │
├────────────────────┼─────────┼──────────────────────┼───────────┼──────────┼──────────┤
│ PRES-2028-DEM-WIN  │ active  │ ...                   │ 52¢       │ Politics │ 2h ago   │
│ AI-AGI-2026        │ active  │ ...                   │ [AWAITING…]│ Tech     │ 5h ago   │
│ FED-RATE-MAR26     │ active  │ ...                   │ 48¢       │ Economics│ 12h ago  │
└────────────────────┴─────────┴──────────────────────┴───────────┴──────────┴──────────┘

Showing 3 new markets (1 unpriced)
```

### 5) Optional Exa research integration

When `--research` flag is set:

1. For each new market, run `kalshi research context <ticker>` equivalent
2. Display a brief summary (title + 1-2 key findings)
3. Warn about cost before proceeding

```bash
$ kalshi scan new-markets --hours 12 --research

This will run Exa research on up to 5 markets (~$0.50-1.00 cost).
Continue? [y/N]: y

New Markets (last 12 hours) + Research

PRES-2028-DEM-WIN (52¢ YES)
  Created: 2h ago | Category: Politics
  Research: Early polling shows Harris leading in key states. No major
  opposition announced yet. Market may be underpriced given incumbent advantage.
  Sources: [1] Reuters, [2] FiveThirtyEight

AI-AGI-2026 [UNPRICED]
  Created: 5h ago | Category: Tech
  Research: Recent Anthropic/OpenAI announcements suggest accelerating
  capabilities. Expert consensus remains 2027-2030 for AGI definitions.
  Sources: [1] arXiv, [2] AI researcher interviews
```

---

## Implementation Plan

### Phase 1: Basic `new-markets` command

1. Add `new_markets` command to `src/kalshi_research/cli/scan.py`
2. Implement newness filtering using `created_time` (fallback to `open_time`)
3. Add `--include-unpriced` flag to bypass placeholder filtering
4. Add `--category` filter (reuse existing category alias logic)
5. Update CLI reference docs

**Files to modify:**
- `src/kalshi_research/cli/scan.py` - New command
- `src/kalshi_research/analysis/scanner.py` - Optional helper for newness check
- `docs/trading/scanner.md` - Documentation
- `.claude/skills/kalshi-cli/CLI-REFERENCE.md` - Skill docs
- `.codex/skills/kalshi-cli/CLI-REFERENCE.md` - Skill docs
- `.gemini/skills/kalshi-cli/CLI-REFERENCE.md` - Skill docs

### Phase 2: Exa research integration (optional)

1. Add `--research` flag
2. Implement research loop with cost warning
3. Format research output inline with market listing

**Files to modify:**
- `src/kalshi_research/cli/scan.py` - Research integration
- Reuse existing `research context` logic from `src/kalshi_research/cli/research.py`

---

## Acceptance Criteria

### Phase 1

- [x] `kalshi scan new-markets` shows markets created in last 24h by default
- [x] `--hours` flag adjusts the lookback window
- [x] `--category` filters by category (politics, tech, etc.)
- [x] `--include-unpriced` shows markets with placeholder quotes (labeled)
- [x] Markets without `created_time` fall back to `open_time` with warning
- [x] `--json` outputs machine-readable format
- [x] Exit code 0 on success (even if no results)

### Phase 2

- [ ] `--research` runs Exa context research on each result
- [ ] Cost warning displayed before proceeding
- [ ] Research results formatted inline with market listing
- [ ] Graceful handling of Exa API errors (show market, skip research)

---

## Test Plan

### Unit tests

```python
def test_new_markets_filters_by_created_time() -> None:
    """Markets older than --hours are excluded."""
    pass

def test_new_markets_includes_unpriced_when_flag_set() -> None:
    """Placeholder quotes (0/100) included with --include-unpriced."""
    pass

def test_new_markets_falls_back_to_open_time() -> None:
    """Markets without created_time use open_time as proxy."""
    pass

def test_new_markets_category_filter() -> None:
    """--category filters results correctly."""
    pass
```

### Integration tests

```python
@pytest.mark.integration
def test_new_markets_live_api() -> None:
    """Smoke test against live API (no auth required)."""
    result = runner.invoke(app, ["scan", "new-markets", "--hours", "168"])
    assert result.exit_code == 0
```

---

## Cross-References

| Document | Relationship |
|----------|--------------|
| DEBT-014 B3 | Source requirement (New Market Alert System) |
| SPEC-031 | Scanner quality profiles (complementary) |
| SPEC-036 | Category filtering (reuse) |
| FUTURE-001 | Exa Research Agent (Phase 2 integration) |

---

## Open Questions

1. **Default hours**: 24h feels right, but should we consider 48h or 72h for weekend coverage?
2. **Research cost cap**: Should `--research` have a `--max-cost` flag to limit spend?
3. **Notification integration**: Should this integrate with `kalshi alerts monitor` for periodic checks?

These can be resolved during implementation or deferred to future iterations.
