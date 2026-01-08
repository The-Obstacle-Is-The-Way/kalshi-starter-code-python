# BUG-005: Missing Research Modules

**Priority:** P3
**Status:** ✅ Fixed (2026-01-07)
**Discovered:** 2026-01-06
**Fixed:** 2026-01-07
**Spec Reference:** SPEC-004 Section 3.1

---

## Summary

Several research modules specified in SPEC-004 are missing from `src/kalshi_research/research/`.

## Expected Files (per SPEC-004)

```
research/
├── __init__.py          ✓ EXISTS
├── thesis.py            ✓ EXISTS
├── backtest.py          ✓ EXISTS
└── notebook_utils.py    ✓ EXISTS
```

## Fix Applied

Implemented the missing modules under `src/kalshi_research/research/`:

- `backtest.py`
- `notebook_utils.py`

## Acceptance Criteria

- [x] `backtest.py` implemented
- [x] `notebook_utils.py` implemented
- [x] Unit tests exist for research modules
- [x] Modules pass strict type checking (`uv run mypy src/ --strict`)
- [ ] Works in Jupyter notebooks (requires local Jupyter environment)
