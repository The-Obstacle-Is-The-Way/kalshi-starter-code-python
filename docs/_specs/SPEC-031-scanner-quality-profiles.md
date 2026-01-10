# SPEC-031: Scanner Quality Profiles (Slop Filtering + “Get In Early” Mode)

**Status:** Draft
**Priority:** P1 (Trading UX / Signal Quality)
**Created:** 2026-01-10
**Owner:** Solo
**Effort:** ~1–2 days

---

## Summary

Improve the market scanner’s default ergonomics so users don’t routinely see low-volume, wide-spread “slop”,
while still preserving a principled way to surface genuinely interesting **new** markets (low volume but
actionable early entry).

This is a “quality profile” layer on top of existing scanner logic.

---

## Goals

1. Provide **opinionated presets** for `kalshi scan opportunities` that:
   - hide obvious garbage by default (min volume, max spread)
   - are explicit and user-selectable (no hidden magic)
2. Add an **Early** profile that allows low volume only when liquidity/spread signals indicate tradability.
3. Make output **self-explanatory** (why a result was included / excluded).
4. Preserve backward compatibility:
   - existing flags keep working
   - “raw” mode matches current behavior

---

## Non-Goals

- No new alpha models, no AI.
- No changes to market discovery (API) strategy (that’s SPEC-029).
- No changes to liquidity scoring math (that’s already implemented; we only reuse it).

---

## Current State (SSOT)

### Scanner logic (good)

- Scanner already supports:
  - `min_volume_24h` and `max_spread` for close-race scanning
  - skipping placeholder quotes (`0/0` and `0/100`)
  - tradeability checks via status + close_time
  (SSOT: `src/kalshi_research/analysis/scanner.py`)

### CLI defaults (slop-prone)

- `kalshi scan opportunities` defaults:
  - `--min-volume 0`
  - `--max-spread 100`
  - no liquidity filter unless user opts in
  (SSOT: `src/kalshi_research/cli/scan.py`)

This makes it easy to surface technically “close race” markets that are not realistically tradable.

### Liquidity scoring exists (orderbook-based)

- Liquidity analysis is implemented and exposed via:
  - `kalshi market liquidity`
  - optional `--min-liquidity` / `--show-liquidity` in `scan opportunities`
  (SSOT: `src/kalshi_research/analysis/liquidity.py`, `src/kalshi_research/cli/scan.py`)

---

## Design

### 1) Introduce “quality profiles” as first-class presets

Add a `--profile` option to `kalshi scan opportunities`:

| Profile | Purpose | Defaults |
|---|---|---|
| `raw` | current behavior | `min_volume=0`, `max_spread=100`, `min_liquidity=None` |
| `tradeable` | baseline tradability | `min_volume=1000`, `max_spread=10`, `min_liquidity=None` |
| `liquid` | higher confidence execution | `min_volume=5000`, `max_spread=5`, `min_liquidity=60` |
| `early` | allow low volume only when book quality is good | `min_volume=100`, `max_spread=5`, `min_liquidity=40`, plus “new market” gating |

Rules:

- Explicit user flags override profile defaults (e.g., `--profile liquid --min-volume 1000` uses 1000).
- `raw` must remain the exact current default behavior for backwards compatibility.
- The CLI default should become `--profile tradeable` **only if** we’re comfortable changing behavior; otherwise
  keep default profile as `raw` but print a guidance line recommending `--profile tradeable`.

### 2) “Early” profile gating (avoid “slop masquerading as early”)

Early markets can be valuable, but only when execution is viable.

Early profile includes low volume only when:

1. **Spread constraint:** `spread <= 5¢` (already computed)
2. **Orderbook-based liquidity constraint:** `liquidity_score >= 40` (requires orderbook fetch)
3. **Not placeholders:** already enforced by scanner
4. **Market is “new”:**
   - Prefer `Market.created_time` when present; otherwise fall back to `open_time`
   - Require `now - created_time <= 72h` (configurable)

If created_time is missing from the API response, the profile still works using `open_time`, but should display
a warning that “newness” was approximated.

### 3) Output: explain “why”

Add a `Reasons` column (or per-row flags) when using a profile:

- `LOW_VOL_OK_EARLY`
- `WIDE_SPREAD_SKIPPED`
- `LOW_LIQUIDITY_SKIPPED`
- `PLACEHOLDER_QUOTES_SKIPPED`

At minimum:
- show a one-line summary after the table: “Filtered 1,243 markets → 12 results (reasons: …)”

This prevents confusion (“why did it show garbage?”).

---

## Implementation Plan

### Phase 1: Profiles as CLI presets (no scanner changes)

1. Add `ScanProfile` enum in `src/kalshi_research/cli/scan.py`.
2. Add `--profile` option and map it to default values for:
   - `min_volume`, `max_spread`, `min_liquidity`, `liquidity_depth`
3. Preserve existing defaults in `raw`.
4. Update docs:
   - `docs/trading/scanner.md` to recommend `--profile tradeable` for normal use.

### Phase 2: Early gating (small scanner/CLI refactor)

1. Add “newness” gating in the CLI layer (before liquidity fetch) so we don’t fetch orderbooks for obviously
   irrelevant markets.
2. Compute liquidity only for the reduced candidate set (already supported by current `scan_top_n` logic).

### Phase 3: Better explanation output

1. Track counters for filter drop reasons.
2. Print summary counts and optional per-row flags.

---

## Acceptance Criteria

- [ ] Running `uv run kalshi scan opportunities --profile tradeable` produces materially less slop out-of-the-box.
- [ ] `--profile early` surfaces some low-volume markets but still enforces tight spread + liquidity score.
- [ ] Existing invocations without `--profile` continue to work exactly as before (unless we intentionally change the default and document it).
- [ ] Docs reflect the recommended operational defaults and explicitly explain the tradeoff (“slop vs early”).
