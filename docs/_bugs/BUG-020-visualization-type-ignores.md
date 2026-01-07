# BUG-020: Visualization Type Ignores

## Priority
P5 (Won't Fix) - Tooling Limitation

## Description
The `visualization.py` module contains `# type: ignore` comments due to incomplete type stubs in `matplotlib` and `pandas`.

## Location
- `src/kalshi_research/analysis/visualization.py`

## Impact
- Minimal. This is a known limitation of the scientific python ecosystem.

## Proposed Fix
- None required currently. Wait for better library support.
