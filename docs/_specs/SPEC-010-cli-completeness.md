# SPEC-010: CLI Completeness

**Status:** Draft
**Priority:** P2
**Depends On:** SPEC-005 (Alerts), SPEC-006 (Correlation), SPEC-007 (Metrics), SPEC-008 (Backtest)

---

## Overview

Expose all existing modules through CLI commands. Currently, several powerful modules exist but have NO CLI interface:

| Module | CLI Commands | Status |
|--------|--------------|--------|
| `alerts/` | None | ❌ Missing |
| `analysis/calibration.py` | None | ❌ Missing |
| `analysis/correlation.py` | None | ❌ Missing |
| `analysis/metrics.py` | None | ❌ Missing |
| `research/thesis.py` | None | ❌ Missing |
| `research/backtest.py` | None | ❌ Missing |

---

## Requirements

### 1. Alerts CLI (`kalshi alerts`)

```bash
# List active alerts
kalshi alerts list

# Add price alert
kalshi alerts add price TICKER --above 60 --notify console
kalshi alerts add price TICKER --below 40 --notify webhook --url https://...

# Add volume alert
kalshi alerts add volume TICKER --above 10000

# Add spread alert
kalshi alerts add spread TICKER --above 5

# Remove alert
kalshi alerts remove <alert-id>

# Start monitoring (runs in foreground)
kalshi alerts monitor

# Start monitoring daemon (background)
kalshi alerts monitor --daemon
```

**Implementation:**
- Add `alerts_app = typer.Typer()` to `cli.py`
- Wire up `AlertMonitor`, `PriceThresholdCondition`, etc.
- Store alerts in SQLite (new table) or JSON file

### 2. Analysis CLI (`kalshi analysis`)

```bash
# Calibration analysis
kalshi analysis calibration --days 30
kalshi analysis calibration --output calibration_report.json

# Correlation analysis
kalshi analysis correlation --event EVENT_TICKER
kalshi analysis correlation --tickers TICK1,TICK2,TICK3

# Market metrics
kalshi analysis metrics TICKER
kalshi analysis metrics TICKER --history --days 7
```

**Implementation:**
- Add `analysis_app = typer.Typer()` to `cli.py`
- Wire up `CalibrationAnalyzer`, `CorrelationAnalyzer`, `ProbabilityMetrics`
- Output as Rich tables or JSON

### 3. Research CLI (`kalshi research`)

```bash
# Thesis management
kalshi research thesis create "Trump wins" --markets TICK1,TICK2 --direction yes
kalshi research thesis list
kalshi research thesis track THESIS_ID
kalshi research thesis close THESIS_ID --outcome win|loss

# Backtesting
kalshi research backtest --strategy momentum --start 2024-01-01 --end 2024-12-31
kalshi research backtest --strategy mean-reversion --ticker TICKER
kalshi research backtest results --format table|json|csv
```

**Implementation:**
- Add `research_app = typer.Typer()` to `cli.py`
- Wire up `ThesisTracker`, `Backtester`
- Store theses in SQLite

### 4. Enhanced Scan CLI

Extend existing `kalshi scan` with more options:

```bash
# Current
kalshi scan opportunities --filter close-race

# New additions
kalshi scan opportunities --filter expiring-soon --hours 24
kalshi scan opportunities --min-volume 1000
kalshi scan opportunities --category politics|economics|sports
kalshi scan arbitrage  # Find mispriced related markets
kalshi scan movers --period 1h  # Biggest price moves
```

---

## CLI Structure After Implementation

```
kalshi
├── version
├── data
│   ├── init
│   ├── sync-markets
│   ├── snapshot
│   ├── collect
│   ├── export
│   └── stats
├── market
│   ├── get
│   ├── list
│   └── orderbook
├── scan
│   ├── opportunities
│   ├── arbitrage      # NEW
│   └── movers         # NEW
├── alerts             # NEW
│   ├── list
│   ├── add
│   ├── remove
│   └── monitor
├── analysis           # NEW
│   ├── calibration
│   ├── correlation
│   └── metrics
└── research           # NEW
    ├── thesis
    │   ├── create
    │   ├── list
    │   ├── track
    │   └── close
    └── backtest
```

---

## Acceptance Criteria

- [ ] `kalshi alerts list/add/remove/monitor` works
- [ ] `kalshi analysis calibration/correlation/metrics` works
- [ ] `kalshi research thesis create/list/track/close` works
- [ ] `kalshi research backtest` works
- [ ] `kalshi scan arbitrage` works
- [ ] `kalshi scan movers` works
- [ ] All commands have `--help` documentation
- [ ] All commands handle errors gracefully (no stack traces for user errors)

---

## Testing

```bash
# Test alerts
kalshi alerts add price TEST-TICKER --above 50
kalshi alerts list
kalshi alerts remove 1

# Test analysis
kalshi analysis calibration --days 7
kalshi analysis metrics SOME-TICKER

# Test research
kalshi research thesis create "Test thesis" --markets TICK1
kalshi research thesis list
```

---

## Notes

- All new commands should follow existing CLI patterns (typer + rich)
- Use async where appropriate (alerts monitor)
- Store persistent data in SQLite alongside market data
- Consider adding `--json` flag to all commands for scripting
