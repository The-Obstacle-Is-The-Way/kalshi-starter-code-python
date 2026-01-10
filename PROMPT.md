# Kalshi Research - Ralph Wiggum Loop Prompt

You are implementing specs, fixing bugs, debt, and TODOs in a Kalshi prediction market research platform.
This prompt runs headless via:

```bash
while true; do
  claude --dangerously-skip-permissions -p "$(cat PROMPT.md)"
  sleep 2
done
```

## First Action: Read State

**IMMEDIATELY** read state files:
```bash
cat PROGRESS.md
```

Then read the relevant documentation:
```bash
cat docs/_bugs/README.md
cat docs/_debt/README.md
cat docs/_todo/README.md
cat docs/_specs/README.md
```

## SPEC-* Self-Review Protocol (APPLY FIRST)

**Before picking up a new task**, check if the MOST RECENTLY completed item is a `SPEC-*` WITHOUT a `[REVIEWED]` marker.

If yes, **THIS ITERATION IS A REVIEW ITERATION**:

1. Read the spec doc and its acceptance criteria
2. Verify the implementation matches ALL acceptance criteria
3. Apply the Critical Review Prompt (below) to your own prior work
4. Check for half-measures:
   - Are there TODO comments that should be resolved?
   - Do tests cover all acceptance criteria?
   - Does SSOT (code) match the spec?
5. **If issues found**:
   - Create a fixup task in PROGRESS.md (e.g., `[ ] **SPEC-028-FIX**: Fix missing tests`)
   - Mark the original as `[NEEDS-FIX]` instead of `[REVIEWED]`
   - Commit and exit
6. **If verified clean**:
   - Add `[REVIEWED]` marker to the spec line
   - Append to Work Log: "SPEC-XXX reviewed and verified"
   - Commit and exit (do NOT start next task this iteration)

## Your Task This Iteration

1. Check for unreviewed SPEC-* (see above) - if found, do review, then exit
2. Find the **FIRST** unchecked `[ ]` item in PROGRESS.md
3. Read the corresponding doc: `docs/_bugs/BUG-XXX*.md`, `docs/_debt/DEBT-XXX*.md`, `docs/_todo/TODO-XXX*.md`, or `docs/_specs/SPEC-XXX*.md`
4. **READ THE ACCEPTANCE CRITERIA** in the task doc - you MUST complete ALL of them
5. Apply the **Critical Review Prompt** (below) to any external feedback and to your own assumptions
6. Complete that ONE item fully (all acceptance criteria met, tests pass, quality checks pass)
7. **UPDATE THE TASK DOC** - check off `[x]` each acceptance criterion you completed
8. Check off the item in PROGRESS.md: `[ ]` → `[x]` (ONLY if all acceptance criteria are `[x]`)
9. Append a short entry to PROGRESS.md "Work Log" (what changed + commands run)
10. **ATOMIC COMMIT** (see format below)
11. Exit

**DO NOT** attempt multiple tasks. One task per iteration.

## Critical Review Prompt (MANDATORY)

Before changing code/docs based on feedback (human, CodeRabbit, another model, your own prior output), apply:

```text
Review the claim or feedback (it may be from an internal or external agent). Validate every claim from first principles. If—and only if—it's true and helpful, update the system to align with the SSOT, implemented cleanly and completely (Rob C. Martin discipline). Find and fix all half-measures, reward hacks, and partial fixes if they exist. Be critically adversarial with good intentions for constructive criticism. Ship the exact end-to-end implementation we need.
```

## A++ STANDARD: Acceptance Criteria Enforcement

**CRITICAL**: A task is NOT complete until ALL acceptance criteria in the task doc are checked off.

Before marking ANY task complete, verify:
1. Read the task doc's **Acceptance Criteria** section
2. EVERY `[ ]` criterion MUST become `[x]`
3. If you only complete SOME criteria, the task stays `[ ]` in PROGRESS.md
4. Update the task doc to show which criteria are done with `[x]`

**Partial implementations are FAILURES.** Do not check off PROGRESS.md until ALL criteria pass.

## Atomic Commit Format

```bash
git add -A && git commit -m "$(cat <<'EOF'
[TASK-ID] Brief description

- What was implemented/fixed
- Tests added/updated
- Quality gates passed
- Acceptance criteria: X/Y complete
EOF
)"
```

**Examples:**
- `[SPEC-028] Implement: Topic search via FTS5`
- `[SPEC-028-REVIEW] Verify: All acceptance criteria met`
- `[BUG-048] Fix: Allow negative liquidity values`

## Quality Gates (MUST PASS)

Before marking ANY task complete:
```bash
uv run pre-commit install         # ONCE per clone (if hooks not installed)
uv run pre-commit run --all-files # ALWAYS before any commit
uv run ruff check .           # No lint errors
uv run ruff format --check .  # Properly formatted
uv run mypy src/              # No type errors
uv run pytest tests/unit -v   # All tests pass
```

If ANY check fails, fix it before proceeding.

## TDD Workflow (When Writing Code)

1. **RED**: Write/update test first
2. **GREEN**: Write minimal code to pass
3. **REFACTOR**: Clean up, keep tests green

## Guardrails

1. **Check for unreviewed SPEC-* first**
2. **ONE task per iteration**
3. **Read PROGRESS.md first**
4. **Read the task doc (BUG-XXX.md, etc.)**
5. **Verify ALL acceptance criteria are addressed**
6. **Quality gates must pass**
7. **Update task doc acceptance criteria checkboxes**
8. **Mark PROGRESS.md task complete ONLY if ALL criteria done**
9. **Commit before exit**
10. **Exit when done**

## BEFORE EXIT CHECKLIST (MANDATORY)

**You MUST complete ALL of these steps before exiting:**

```bash
# 1. Run ALL quality gates (never commit without these)
uv run pre-commit run --all-files
uv run ruff check .
uv run ruff format .
uv run mypy src/
uv run pytest tests/unit -v

# 1b. If docs changed, validate site build
uv run mkdocs build --strict

# 2. Verify acceptance criteria
# - Read task doc's Acceptance Criteria section
# - Ensure ALL criteria are [x] checked
# - If any are [ ], do NOT mark PROGRESS.md as complete

# 3. Stage ALL changes
git add -A

# 4. Verify nothing is unstaged
git status

# 5. Commit with proper message
git commit -m "[TASK-ID] Brief description"
```

**CRITICAL - Do NOT exit if:**

- `git status` shows unstaged changes
- Any quality gate failed
- You haven't committed
- Task doc has unchecked acceptance criteria but PROGRESS.md shows `[x]`

## File Locations

- Bugs: `docs/_bugs/BUG-*.md`
- Debt: `docs/_debt/DEBT-*.md`
- TODOs: `docs/_todo/TODO-*.md`
- Specs: `docs/_specs/SPEC-*.md`
- Source: `src/kalshi_research/`
- Tests: `tests/unit/`, `tests/integration/`
- Skills: `.claude/skills/`, `.codex/skills/`, `.gemini/skills/` (keep in sync)

## Completion

When ALL items in PROGRESS.md are checked AND all quality gates pass, exit cleanly.
The loop operator verifies via PROGRESS.md state, not output parsing.

**A++ Standard means:**
- ALL PROGRESS.md items are `[x]`
- ALL SPEC-* items have `[REVIEWED]` markers
- ALL task doc acceptance criteria are `[x]`
- ALL quality gates pass
- Clean git working tree
