# BUG-032: `kalshi scan arbitrage` silently truncates tickers for correlation scan (P3)

**Priority:** P3 (Misleading/incomplete results)
**Status:** ✅ Fixed (2026-01-07)
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Spec:** SPEC-010-cli-completeness.md
**Checklist Ref:** CODE_AUDIT_CHECKLIST.md Section 1 (Silent Failures), Section 15 (Silent Fallbacks)

---

## Summary

`kalshi scan arbitrage` limited historical correlation analysis to the first 50 markets:

```python
tickers = [m.ticker for m in markets[:50]]
```

This produced incomplete results without any indication to the user.

---

## Root Cause

The CLI used a hard-coded slice (`markets[:50]`) as a performance guardrail but did not:

- expose it as a CLI option, or
- warn when truncation occurred.

---

## Fix Applied

**File:** `src/kalshi_research/cli.py`

- Add `--tickers-limit` option (default `50`)
- Support `--tickers-limit 0` to disable truncation (analyze all tickers)
- Print an explicit warning when truncation occurs

---

## Regression Tests Added

- `tests/unit/test_cli_extended.py::test_scan_arbitrage_warns_when_tickers_truncated`

---

## Acceptance Criteria

- [x] CLI warns when correlation analysis is truncated
- [x] CLI exposes `--tickers-limit` to control/disable truncation
- [x] Regression test passes

