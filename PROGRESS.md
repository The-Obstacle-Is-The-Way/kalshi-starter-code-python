# Kalshi Research Platform — Ralph Wiggum Progress Tracker

**Last Updated:** 2026-01-13
**Status:** Idle (no active queue)
**Purpose:** State file for the Ralph Wiggum loop (see `docs/_ralph-wiggum/protocol.md`)

---

## Active Queue

No active items.

To start a new loop run:

1. Create a sandbox branch for Ralph work.
2. Add tasks below as checklist items (one task per line).
3. Run the loop using `PROMPT.md`.

Guidelines:

- Prefer referencing an existing task doc: `docs/_bugs/BUG-*.md`, `docs/_debt/DEBT-*.md`, `docs/_specs/SPEC-*.md`, `docs/_future/*.md`.
- SPEC-* tasks require a follow-up review iteration and a `[REVIEWED]` marker.

<!-- Template (uncomment and edit when ready)
  ## Phase 1: Bugs
  - [ ] **BUG-###**: Short description → docs/_bugs/BUG-###-....
  ## Phase 2: Debt
  - [ ] **DEBT-###**: Short description → docs/_debt/DEBT-###-....
  ## Phase 3: Specs
  - [ ] **SPEC-###**: Short description → docs/_specs/SPEC-###-....
  ## Phase 4: Final Verification
  - [ ] **FINAL-GATES**: All quality gates pass
-->

---

## Work Log

- 2026-01-13: Reset PROGRESS.md/PROMPT.md templates (idle queue).
- 2026-01-10: Fixed portfolio P&L integrity (FIFO realized P&L + unknown handling), updated BUG-056/057, ran `uv run pre-commit run --all-files` and `uv run mkdocs build --strict`
- 2026-01-10: Skills refactor - created `kalshi-ralph-wiggum` skill, simplified `kalshi-codebase`, enhanced PROMPT.md with SPEC-* self-review protocol, verified SPEC-029/032 against SSOT
- 2026-01-10: Prep for spec implementation (audited SPEC-028..034, added `kalshi-codebase` skill, updated Ralph prompt/protocol)
- 2026-01-09: Phase 1-8 complete (all bugs, debt, TODOs resolved)

---

## Completion Criteria

The queue is complete when there are no unchecked items (no lines matching the unchecked-task pattern at column 0).
The loop operator should verify completion via this file’s state, not by parsing model output.
