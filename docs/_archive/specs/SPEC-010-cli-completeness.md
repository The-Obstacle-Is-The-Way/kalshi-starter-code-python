# SPEC-010: CLI Completeness

**Status:** ✅ Implemented
**Priority:** P2
**Depends On:** SPEC-005 (Alerts), SPEC-006 (Correlation), SPEC-007 (Metrics), SPEC-008 (Backtest)

---

## Overview

Expose platform functionality through a Typer CLI (`kalshi`) with Rich output.

| Module | CLI Commands | Status |
|--------|--------------|--------|
| `alerts/` | `kalshi alerts ...` | ✅ Implemented |
| `analysis/calibration.py` | `kalshi analysis calibration` | ✅ Implemented |
| `analysis/correlation.py` | `kalshi analysis correlation` | ✅ Implemented |
| `analysis/metrics.py` | `kalshi analysis metrics` | ✅ Implemented |
| `research/thesis.py` | `kalshi research thesis ...` | ✅ Implemented |
| `research/backtest.py` | `kalshi research backtest` | ✅ Implemented |

---

## Requirements

### 1. Alerts CLI (`kalshi alerts`)

```bash
# List active alerts
kalshi alerts list

# Add price alert
kalshi alerts add price TICKER --above 0.60
kalshi alerts add price TICKER --below 0.40

# Add volume alert
kalshi alerts add volume TICKER --above 10000

# Add spread alert
kalshi alerts add spread TICKER --above 5

# Remove alert
kalshi alerts remove <alert-id>

# Start monitoring (runs in foreground)
kalshi alerts monitor

# Start monitoring daemon (background)
# `--daemon` starts a detached background process and logs to `data/alert_monitor.log`.
kalshi alerts monitor --daemon

# Run a single check and exit (testable / cron-friendly)
kalshi alerts monitor --once
```

**Implementation:**
- Add `alerts_app = typer.Typer()` to `cli.py`
- Wire up `AlertMonitor`, `PriceThresholdCondition`, etc.
- Store alerts in `data/alerts.json` (JSON file)

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
kalshi research thesis create "Trump wins" --markets TICK1,TICK2 --your-prob 0.6 --market-prob 0.5 --confidence 0.7
kalshi research thesis list
kalshi research thesis show THESIS_ID
kalshi research thesis resolve THESIS_ID --outcome yes|no|void

# Backtesting
kalshi research backtest --strategy momentum --start 2024-01-01 --end 2024-12-31
kalshi research backtest --strategy mean-reversion --ticker TICKER
kalshi research backtest results --format table|json|csv
```

**Implementation:**
- Add `research_app = typer.Typer()` to `cli.py`
- Wire up `ThesisTracker`, `Backtester`
- Store theses in `data/theses.json` (JSON file)

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
    │   ├── show
    │   └── resolve
    └── backtest
```

---

## Acceptance Criteria

- [x] `kalshi alerts list/add/remove/monitor` works (`--once` and `--daemon` supported for testability/ops)
- [x] `kalshi analysis calibration/correlation/metrics` works (graceful empty-data handling)
- [x] `kalshi research thesis create/list/show/resolve` works
- [x] `kalshi research backtest` runs (real DB-backed output)
- [x] `kalshi scan arbitrage` works
- [x] `kalshi scan movers` works
- [x] All commands have `--help` documentation
- [x] All commands handle user errors gracefully (no stack traces for expected user errors)

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
- Alerts/thesis persistence currently uses JSON files under `data/`

---

## Implementation References

- `src/kalshi_research/cli.py`
- `tests/integration/cli/test_cli_commands.py`
- `tests/e2e/test_data_pipeline.py`
- `tests/e2e/test_analysis_pipeline.py`
