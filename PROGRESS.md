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
- [ ] **QUALITY-003**: Ensure all quality gates pass: `ruff check`, `ruff format --check`, `mypy src/`, `pytest`

## Phase 3: Extended Features (SPEC-005 through SPEC-008)

These implement the user's original requirements beyond core platform:

- [ ] **SPEC-005**: Alerts & Notifications → See `docs/_specs/SPEC-005-alerts-notifications.md`
  - Creates `src/kalshi_research/alerts/` module
  - Implements AlertCondition, AlertMonitor, Notifiers
  - Satisfies BUG-006 ("notify me when conditions met")

- [ ] **SPEC-006**: Event Correlation Analysis → See `docs/_specs/SPEC-006-event-correlation-analysis.md`
  - Creates `src/kalshi_research/analysis/correlation.py`
  - Implements CorrelationAnalyzer, ArbitrageDetector
  - Satisfies BUG-004 (correlation.py)

- [ ] **SPEC-007**: Probability Tracking & Visualization → See `docs/_specs/SPEC-007-probability-tracking-visualization.md`
  - Creates `src/kalshi_research/analysis/metrics.py`
  - Creates `src/kalshi_research/analysis/visualization.py`
  - Satisfies BUG-004 (metrics.py, visualization.py)

- [ ] **SPEC-008**: Research Notebooks & Backtesting → See `docs/_specs/SPEC-008-research-notebooks-backtesting.md`
  - Creates `notebooks/` directory with templates
  - Creates `src/kalshi_research/research/backtest.py`
  - Creates `src/kalshi_research/research/notebook_utils.py`
  - Satisfies BUG-003 and BUG-005

## Phase 4: Final Verification

- [ ] **FINAL-001**: All 4 quality gates pass (ruff check, ruff format, mypy, pytest)
- [ ] **FINAL-002**: Test coverage >80%
- [ ] **FINAL-003**: CI/CD passes on Python 3.11, 3.12, 3.13
- [ ] **FINAL-004**: All CLI commands work: `kalshi --help`, `kalshi data --help`, `kalshi scan --help`
- [ ] **FINAL-005**: All imports work without error

---

## How to Use This File

**For each Ralph Wiggum iteration:**

1. Read this file to find the FIRST unchecked `[ ]` item
2. Complete that ONE item fully
3. Change `[ ]` to `[x]` for the completed item
4. Commit your changes
5. Exit

**Example:**
```bash
# Read current state
cat PROGRESS.md

# Find: [ ] **BUG-002**: Set up Alembic migrations
# Complete that task
# Update this file: [x] **BUG-002**: Set up Alembic migrations
# Commit and exit
```

---

## Completion Criteria

When ALL boxes are checked AND all quality gates pass, the loop can output:

```
<promise>KALSHI RESEARCH PLATFORM COMPLETE</promise>
```
