# BUG-009: Incomplete CLI Commands (SPEC-010)

**Priority:** P3 (Non-blocking enhancement)
**Status:** Open
**Found:** 2026-01-07
**Spec:** SPEC-010-cli-completeness.md

---

## Summary

SPEC-010 specified several CLI commands that were not implemented. The core functionality exists but CLI exposure is incomplete.

---

## Missing Commands

### 1. `kalshi alerts monitor`

**Specified:**
```bash
# Start monitoring (runs in foreground)
kalshi alerts monitor

# Start monitoring daemon (background)
kalshi alerts monitor --daemon
```

**Status:** NOT IMPLEMENTED

**Impact:** Users cannot run continuous alert monitoring from CLI. The `AlertMonitor` class exists but has no CLI exposure.

---

### 2. `kalshi analysis correlation`

**Specified:**
```bash
kalshi analysis correlation --event EVENT_TICKER
kalshi analysis correlation --tickers TICK1,TICK2,TICK3
```

**Status:** NOT IMPLEMENTED

**Impact:** `CorrelationAnalyzer` exists in `src/kalshi_research/analysis/correlation.py` but has no CLI exposure.

---

### 3. `kalshi scan arbitrage`

**Specified:**
```bash
kalshi scan arbitrage  # Find mispriced related markets
```

**Status:** NOT IMPLEMENTED

**Impact:** `ArbitrageDetector` exists in `src/kalshi_research/analysis/correlation.py` but has no CLI exposure.

---

### 4. `kalshi scan movers`

**Specified:**
```bash
kalshi scan movers --period 1h  # Biggest price moves
```

**Status:** NOT IMPLEMENTED

**Impact:** Would require tracking price changes over time. Data infrastructure exists but no scanner implementation.

---

## Implemented CLI Structure (Current)

```
kalshi
├── version           ✅
├── data              ✅ (init, sync-markets, snapshot, collect, export, stats)
├── market            ✅ (get, list, orderbook)
├── scan
│   └── opportunities ✅
│   └── arbitrage     ❌ MISSING
│   └── movers        ❌ MISSING
├── alerts
│   ├── list          ✅
│   ├── add           ✅
│   ├── remove        ✅
│   └── monitor       ❌ MISSING
├── analysis
│   ├── calibration   ✅
│   ├── metrics       ✅
│   └── correlation   ❌ MISSING
├── research
│   ├── thesis        ✅ (create, list, show, resolve)
│   └── backtest      ✅
└── portfolio         ✅ (sync, positions, pnl, balance, history)
```

---

## Acceptance Criteria

- [ ] `kalshi alerts monitor` starts AlertMonitor in foreground
- [ ] `kalshi alerts monitor --daemon` runs in background
- [ ] `kalshi analysis correlation --event X` shows correlated markets
- [ ] `kalshi scan arbitrage` finds mispriced related markets
- [ ] `kalshi scan movers --period 1h` shows biggest price moves

---

## Implementation Notes

1. **alerts monitor**: Wire up existing `AlertMonitor` class with asyncio event loop
2. **analysis correlation**: Wire up existing `CorrelationAnalyzer`
3. **scan arbitrage**: Wire up existing `ArbitrageDetector`
4. **scan movers**: Requires new `MoverScanner` that queries price snapshots

---

## Priority Justification

**P3 (Low)** because:
- Core functionality exists, just missing CLI exposure
- Users can use Python API directly
- Not blocking any other features
- Nice-to-have for power users
