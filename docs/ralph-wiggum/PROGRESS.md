# Kalshi Research Platform - Progress Tracker

**Last Updated:** 2026-01-06
**Purpose:** State file for Ralph Wiggum loop - each iteration reads this to find next task

---

## Phase 1: Bug Fixes (BLOCKING)

These must be fixed before claiming "complete":

- [x] **BUG-001**: Add `scan` CLI command → `kalshi scan opportunities` works
- [x] **BUG-002**: Set up Alembic migrations → `alembic/` configured with initial migration
- [x] **BUG-007**: Fix CI/CD test failures → See `docs/_bugs/BUG-007-cicd-test-failures.md`

## Phase 2: Quality Fixes

Fix any remaining code quality issues:

- [x] **QUALITY-001**: Fix mypy error in `src/kalshi_research/cli.py:467`
- [x] **QUALITY-002**: Fix ruff import sorting in `alembic/env.py`
- [x] **QUALITY-003**: Ensure all quality gates pass: `ruff check`, `ruff format --check`, `mypy src/`, `pytest`

## Phase 3: Extended Features (SPEC-005 through SPEC-008)

These implement the user's original requirements beyond core platform:

- [x] **SPEC-005**: Alerts & Notifications → See `docs/_specs/SPEC-005-alerts-notifications.md`
  - Creates `src/kalshi_research/alerts/` module
  - Implements AlertCondition, AlertMonitor, Notifiers
  - Satisfies BUG-006 ("notify me when conditions met")

- [x] **SPEC-006**: Event Correlation Analysis → See `docs/_specs/SPEC-006-event-correlation-analysis.md`
  - Creates `src/kalshi_research/analysis/correlation.py`
  - Implements CorrelationAnalyzer, ArbitrageDetector
  - Satisfies BUG-004 (correlation.py)

- [x] **SPEC-007**: Probability Tracking & Visualization → See `docs/_specs/SPEC-007-probability-tracking-visualization.md`
  - Creates `src/kalshi_research/analysis/metrics.py`
  - Creates `src/kalshi_research/analysis/visualization.py`
  - Satisfies BUG-004 (metrics.py, visualization.py)

- [x] **SPEC-008**: Research Notebooks & Backtesting → See `docs/_specs/SPEC-008-research-notebooks-backtesting.md`
  - Creates `notebooks/` directory with templates
  - Creates `src/kalshi_research/research/backtest.py`
  - Creates `src/kalshi_research/research/notebook_utils.py`
  - Satisfies BUG-003 and BUG-005

## Phase 4: Final Verification

- [x] **FINAL-001**: All 4 quality gates pass (ruff check, ruff format, mypy, pytest)
- [x] **FINAL-002**: Test coverage >80% (87% achieved)
- [x] **FINAL-003**: CI/CD passes on Python 3.11, 3.12, 3.13
- [x] **FINAL-004**: All CLI commands work: `kalshi --help`, `kalshi data --help`, `kalshi scan --help`
- [x] **FINAL-005**: All imports work without error

## Phase 5: Cleanup (Optional)

Non-blocking cleanup tasks:

- [x] **BUG-008**: Restructure tests to mirror src/ → See `docs/_bugs/BUG-008-inconsistent-test-structure.md`
  - Move flat test files (test_api_*.py, test_data_*.py, test_analysis_*.py) into nested directories
  - Should match: api/, data/, analysis/, alerts/, research/
  - Use `git mv` to preserve history

## Phase 6: Platform Completeness (Future)

These specs complete the full vision from the original requirements:

- [x] **SPEC-009**: Legacy Cleanup & Documentation → See `docs/_specs/SPEC-009-cleanup-documentation.md`
  - Remove `clients.py`, `main.py`, `requirements.txt` from root
  - Rewrite README.md for new platform
  - Create QUICKSTART.md and USAGE.md

- [x] **SPEC-010**: CLI Completeness → See `docs/_specs/SPEC-010-cli-completeness.md`
  - Add `kalshi alerts` CLI commands (list, add, remove, monitor)
  - Add `kalshi analysis` CLI commands (calibration, correlation, metrics)
  - Add `kalshi research` CLI commands (thesis, backtest)
  - Expose all existing modules through CLI

- [x] **SPEC-011**: Manual Trading Support → See `docs/_specs/SPEC-011-manual-trading-support.md`
  - Add `kalshi portfolio` CLI commands (sync, positions, pnl, balance, history)
  - Track positions and P&L from actual trades (read-only, no automation)
  - Link theses to positions ("Did my research play out?")

## Phase 7: Polish & DevX (Optional)

Minor gaps and developer experience improvements:

- [x] **BUG-009**: Complete missing CLI commands → See `docs/_bugs/BUG-009-incomplete-cli-commands.md`
  - Add `kalshi alerts monitor` (AlertMonitor CLI exposure)
  - Add `kalshi analysis correlation` (CorrelationAnalyzer CLI)
  - Add `kalshi scan arbitrage` (ArbitrageDetector CLI)
  - Add `kalshi scan movers` (Price movers scanner)

- [x] **BUG-010**: Portfolio-thesis linking → See `docs/_bugs/BUG-010-missing-portfolio-link.md`
  - Add `kalshi portfolio link TICKER --thesis ID`
  - Add `kalshi portfolio suggest-links`
  - Add `--with-positions` flag to thesis show

- [x] **SPEC-012**: Developer Experience → See `docs/_specs/SPEC-012-developer-experience.md`
  - Create Makefile with modern 2026 commands
  - Add VS Code tasks.json (optional)
  - Add CLI quick reference card
  - Add mise.toml for version management

---

## How to Use This File

**For each Ralph Wiggum iteration:**

1. Read this file to find the FIRST unchecked `[ ]` item
2. Complete that ONE item fully
3. Change `[ ]` to `[x]` for the completed item
4. Commit your changes
5. Exit

**Example loop command:**
```bash
MAX=50; for i in $(seq 1 $MAX); do
  claude --dangerously-skip-permissions -p "$(cat PROMPT.md)"
  sleep 2
done
```

---

## Completion Criteria

**Phase 1-6 (Core Platform):** ✅ COMPLETE
- All blocking bugs fixed
- All specs 001-011 implemented
- All quality gates pass
- 325 unit tests passing, ~87% coverage

**Phase 7 (Optional Polish):** ✅ COMPLETE
- BUG-009: CLI completeness (P3) - Fixed
- BUG-010: Portfolio-thesis linking (P4) - Fixed
- SPEC-012: Developer Experience (P3) - Implemented

The platform is fully complete with all optional polish.

When ALL boxes are checked AND all quality gates pass, the loop can output:

```
KALSHI RESEARCH PLATFORM COMPLETE
```
