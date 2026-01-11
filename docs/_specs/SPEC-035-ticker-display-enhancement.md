# SPEC-035: Ticker Display Enhancement

**Status:** Draft
**Priority:** P3 (UX Polish)
**Created:** 2026-01-10
**Source:** `friction.md` - "Ticker Truncation"

---

## Problem Statement

CLI commands truncate long tickers making them unreadable and requiring database queries to see full values.

**Example friction from `friction.md`:**
```
portfolio history truncates long tickers with `...`
Example: `KXNFLAFCCHAMP-25-…` should be queried from `trades` table
```

**Current truncation patterns found in codebase:**
- `market.py:411` - `m.ticker[:30]` (hard 30 char limit)
- `market.py:412` - `m.title[:40] + "..."` (explicit ellipsis)
- `scan.py:124` - `m.title[:50]`
- `scan.py:443` - `tickers_str[:30]`
- `research.py:138` - `result.thesis_id[:15]`
- `research.py:306` - `thesis["title"][:40]`

**Root Cause:** Hardcoded character limits don't adapt to terminal width.

---

## Three Implementation Approaches

### Approach A: Rich `no_wrap=True` + `--full` Flag (RECOMMENDED)

**How it works:**
1. Add `no_wrap=True` to ticker columns in Rich Tables
2. Add `--full` / `-F` flag to disable ALL truncation
3. Let terminal handle horizontal scrolling naturally

**Pros:**
- Minimal code changes
- Works with any terminal width
- User choice via flag
- Rich handles display gracefully

**Cons:**
- May cause horizontal scroll on narrow terminals
- Inconsistent if some commands have flag, others don't

**Implementation:**
```python
# In cli/portfolio.py, cli/market.py, etc.
table.add_column("Ticker", style="cyan", no_wrap=True)

# Add global --full flag
full: Annotated[
    bool,
    typer.Option("--full", "-F", help="Show full tickers without truncation."),
] = False

# Conditional truncation
ticker_display = trade.ticker if full else trade.ticker[:30]
```

---

### Approach B: Adaptive Width Based on Terminal Size

**How it works:**
1. Detect terminal width via `shutil.get_terminal_size()`
2. Calculate available space after fixed columns
3. Dynamically set ticker column width

**Pros:**
- Always fits terminal
- No horizontal scrolling
- Automatic adaptation

**Cons:**
- Complex calculation logic
- May still truncate on narrow terminals
- More code to maintain

**Implementation:**
```python
import shutil

def _ticker_width() -> int:
    """Calculate ticker column width based on terminal."""
    term_width = shutil.get_terminal_size().columns
    # Reserve space for other columns: Date(16) + Side(4) + Action(4) + Qty(6) + Price(8) + Total(10) + padding(20)
    fixed_width = 16 + 4 + 4 + 6 + 8 + 10 + 20
    available = term_width - fixed_width
    return max(20, min(50, available))  # Clamp between 20-50
```

---

### Approach C: Config-Based Column Widths

**How it works:**
1. Add user config file (`~/.kalshi/config.toml`)
2. Allow users to set preferred column widths
3. Fallback to sensible defaults

**Pros:**
- Maximum user control
- Persistent preferences
- Supports power users

**Cons:**
- Significant implementation overhead
- Config file management
- Overkill for this problem

---

## Recommendation: Approach A

**Rationale:**
1. Minimal code changes (add `no_wrap=True` to existing columns)
2. `--full` flag is intuitive and consistent with Unix conventions (`ls -l`)
3. Works for all commands without complex calculations
4. No new dependencies or config files

---

## Implementation Plan

### Phase 1: Add `no_wrap=True` to Ticker Columns

**Files to modify:**

| File | Line | Current | Change |
|------|------|---------|--------|
| `cli/portfolio.py:202` | `add_column("Ticker"...)` | No `no_wrap` | Add `no_wrap=True` |
| `cli/portfolio.py:448` | `add_column("Ticker"...)` | No `no_wrap` | Add `no_wrap=True` |
| `cli/market.py:403` | `add_column("Ticker"...)` | `no_wrap=True` | Already correct |
| `cli/scan.py:116` | Inline build | - | Add `no_wrap=True` |
| `cli/scan.py:573` | `add_column("Ticker"...)` | - | Add `no_wrap=True` |

### Phase 2: Add `--full` Flag to Commands with Truncation

**Commands needing `--full` flag:**
1. `kalshi market list` - truncates at 30 chars
2. `kalshi scan opportunities` - truncates title at 50 chars
3. `kalshi scan arbitrage` - truncates tickers at 30 chars
4. `kalshi scan movers` - truncates title at 40 chars
5. `kalshi research thesis list` - truncates title at 40 chars

**Implementation pattern:**
```python
@app.command("list")
def market_list(
    # ... existing params ...
    full: Annotated[
        bool,
        typer.Option("--full", "-F", help="Show full tickers/titles without truncation."),
    ] = False,
) -> None:
    # ...
    for m in markets[:limit]:
        ticker = m.ticker if full else m.ticker[:30]
        title = m.title if full else (m.title[:40] + ("..." if len(m.title) > 40 else ""))
        table.add_row(ticker, title, ...)
```

### Phase 3: Tests

Add tests verifying:
1. `--full` flag shows complete strings
2. Default behavior still truncates
3. Table renders without errors at various terminal widths

**Test locations:**
- `tests/unit/cli/test_market.py`
- `tests/unit/cli/test_portfolio.py`
- `tests/unit/cli/test_scan.py`

---

## Success Criteria

1. `kalshi portfolio history --full` shows complete tickers
2. `kalshi market list --full` shows complete tickers and titles
3. `kalshi scan opportunities --full` shows complete titles
4. Default behavior unchanged (maintains backwards compatibility)
5. All quality gates pass

---

## API Reference

**Vendor docs:** `docs/_vendor-docs/kalshi-api-reference.md`

Ticker format: `KX{EVENT}-{DATE}[-{VARIANT}]`
Examples:
- Short: `KXBTC-26FEB01` (13 chars)
- Medium: `KXNCAAFSPREAD-26JAN09OREIND-IND3` (33 chars)
- Long: `KXNFLAFCCHAMP-25-KC` (19 chars)

Maximum observed: ~35 chars. Safe display width: 40 chars.

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `cli/portfolio.py` | Add `no_wrap=True`, add `--full` to `history` |
| `cli/market.py` | Add `--full` to `list` |
| `cli/scan.py` | Add `--full` to `opportunities`, `arbitrage`, `movers` |
| `cli/research.py` | Add `--full` to `thesis list` |
| `tests/unit/cli/test_market.py` | Add truncation tests |
| `tests/unit/cli/test_portfolio.py` | Add truncation tests |

---

## Estimated Effort

- Implementation: ~2 hours
- Tests: ~1 hour
- Total: ~3 hours
