# DEBT-024: CLI exit code policy (not found vs empty results)

**Priority:** P3 (Quality + automation ergonomics; not core correctness)
**Status:** Open
**Found:** 2026-01-13
**Verified:** 2026-01-13 - CLI behavior audit + reproduction

---

## Summary

The CLI currently mixes several behaviors for “not found” / “nothing to do” cases:

- Some commands correctly return non-zero for missing resources (e.g., thesis/alerts after 6f67f7a).
- Some commands return non-zero but use inconsistent codes (`Exit(1)` vs `Exit(2)`).
- At least one command returns **success** when a specific requested resource is missing:
  - `kalshi portfolio link <TICKER> --thesis <ID>` exits `0` if no open position exists (BUG-076).

This matters for:
- shell scripting (`set -e`, pipelines),
- automation (cron jobs / wrappers),
- user trust (“it said nothing happened, but it ‘succeeded’”).

---

## Proposed Policy (CLI-friendly, internal-tool-appropriate)

Define a simple contract that matches common CLI expectations without “service-grade” complexity:

1. **Exit `0`**: success
   - Includes “empty list” outcomes for list-style commands (e.g., “No markets found” after filtering).
2. **Exit `2`**: user-facing “not found” or “invalid input”
   - A specific identifier was requested and does not exist (thesis id, alert id, ticker for linking, etc.).
   - Invalid option values (already used in multiple commands).
3. **Exit `1`**: runtime failure
   - API/network errors, DB errors, unexpected exceptions.

Optional refinement:
- When idempotent no-op behavior is desired, expose it explicitly with `--force/-f` (then missing becomes Exit `0`).

---

## Current State (Known Cases)

- ✅ Fixed: `alerts remove`, `research thesis show|resolve|check-invalidation` now return `Exit(2)` when missing (6f67f7a).
- ❌ Bug: `portfolio link` exits `0` on missing position (BUG-076).
- Mixed: some “missing DB file” checks use `Exit(1)` rather than `Exit(2)` (policy decision, not urgent).

---

## Acceptance Criteria

- [ ] Decide and document the exit code contract (this doc is the draft SSOT).
- [ ] Update CLI commands to follow the policy for “specific resource not found”.
- [ ] Add/adjust unit tests to lock in behavior (CLI exit codes).
- [ ] Ensure docs stay accurate (`docs/_debt/DEBT-023-production-maturity-gaps.md`, `docs/developer/cli-reference.md` if needed).
