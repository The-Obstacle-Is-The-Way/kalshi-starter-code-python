# BUG-076: `kalshi portfolio link` exits 0 when the position doesn't exist

**Priority:** P2 (Incorrect success signal; breaks scripting and user expectations)
**Status:** ✅ Fixed
**Found:** 2026-01-13
**Verified:** 2026-01-13 - Reproduced locally
**Fixed:** 2026-01-13
**Affected Code:** `portfolio_link()` in `src/kalshi_research/cli/portfolio.py`

---

## Summary

When a user runs:

```bash
uv run kalshi portfolio link <TICKER> --thesis <THESIS_ID>
```

and there is no open `Position` row for `<TICKER>`, the command prints a warning:

> `No open position found for <TICKER>`

but exits successfully (exit code `0`). This is misleading and makes automation impossible to reason about.

---

## Reproduction

This reproduced on a brand-new empty DB:

```bash
tmpdb=$(mktemp -t kalshi_test_XXXX.db)
uv run kalshi portfolio link KXOAIHARDWARE-27 --thesis THESIS-123 --db "$tmpdb"
echo $?
rm -f "$tmpdb"
```

**Observed (pre-fix):** prints the warning, exits `0`.

**Observed (post-fix):** prints the warning, exits `2`.

---

## Root Cause

`portfolio_link()` returns early when the position isn't found instead of raising a non-zero `typer.Exit`.

---

## Impact

- Users can believe the link succeeded when it did nothing.
- Shell scripts cannot detect failure (exit code is `0`).
- This contradicts the CLI convention introduced in `fix(cli): Return exit code 2 for "not found" errors` (6f67f7a).

---

## Proposed Fix

1. Treat missing open position as "not found" and exit non-zero:
   - `raise typer.Exit(2)` (preferred, align with existing "not found" convention).
2. Optional: add `--force/-f` to make the operation idempotent (missing position becomes a no-op with exit `0`).
3. Add a CLI unit test verifying:
   - missing position → exit `2`
   - (optional) `--force` + missing position → exit `0`

---

## Implemented Fix

- `kalshi portfolio link` now treats a missing open position as "not found" and exits with `typer.Exit(2)`.
- Unit test updated to lock in behavior: `tests/unit/cli/test_portfolio.py::test_portfolio_link_position_not_found`.

---

## Related

| Item | Relationship |
|------|--------------|
| `docs/_archive/debt/DEBT-024-cli-exit-code-policy.md` | Standardized exit code behavior across the CLI |
