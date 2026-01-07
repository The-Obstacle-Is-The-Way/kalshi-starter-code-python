# BUG-003: Missing Notebooks Directory

**Priority:** P2
**Status:** Open
**Discovered:** 2026-01-06
**Spec Reference:** PROMPT.md Phase 5, SPEC-004 Section 3.1

---

## Summary

The `notebooks/` directory with Jupyter notebook templates is missing. SPEC-004 explicitly requires research notebooks for calibration analysis, edge detection, and exploration.

## Expected Behavior

Per SPEC-004 Section 3.1:
```
notebooks/
├── 01_exploration.ipynb    # Initial data exploration
├── 02_calibration.ipynb    # Calibration analysis
├── 03_edge_detection.ipynb # Finding opportunities
└── templates/
    └── market_analysis.ipynb
```

## Current Behavior

```bash
$ ls notebooks/
ls: notebooks/: No such file or directory
```

## Root Cause

The notebooks directory and template files were never created.

## Fix

Create notebooks with proper templates:

1. Create directory structure:
```bash
mkdir -p notebooks/templates
```

2. Create `01_exploration.ipynb` template:
```python
# Cells:
# 1. Import and setup
# 2. Load markets from API
# 3. Basic statistics
# 4. Price distribution
# 5. Volume analysis
```

3. Create `02_calibration.ipynb` template:
```python
# Cells:
# 1. Import CalibrationAnalyzer
# 2. Load historical settlements
# 3. Compute Brier score
# 4. Plot calibration curve
# 5. Brier decomposition analysis
```

4. Create `03_edge_detection.ipynb` template:
```python
# Cells:
# 1. Import EdgeDetector, MarketScanner
# 2. Define your thesis
# 3. Detect edges
# 4. Analyze opportunities
# 5. Track thesis over time
```

## Acceptance Criteria

- [ ] `notebooks/` directory exists
- [ ] `01_exploration.ipynb` loads markets and shows basic stats
- [ ] `02_calibration.ipynb` demonstrates CalibrationAnalyzer usage
- [ ] `03_edge_detection.ipynb` demonstrates EdgeDetector/Scanner usage
- [ ] `templates/market_analysis.ipynb` provides reusable template
- [ ] All notebooks run without errors
