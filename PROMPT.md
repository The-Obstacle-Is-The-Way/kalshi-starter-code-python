# Kalshi Research - Ralph Wiggum Loop Prompt

You are fixing bugs, debt, and TODOs in a Kalshi prediction market research platform.
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
```

## Your Task This Iteration

1. Find the **FIRST** unchecked `[ ]` item in PROGRESS.md
2. Read the corresponding doc: `docs/_bugs/BUG-XXX.md`, `docs/_debt/DEBT-XXX.md`, or `docs/_todo/TODO-XXX.md`
3. **READ THE ACCEPTANCE CRITERIA** in the task doc - you MUST complete ALL of them
4. Complete that ONE item fully (all acceptance criteria met, tests pass, quality checks pass)
5. **UPDATE THE TASK DOC** - check off `[x]` each acceptance criterion you completed
6. Check off the item in PROGRESS.md: `[ ]` → `[x]`
7. **ATOMIC COMMIT** (see format below)
8. Exit

**DO NOT** attempt multiple tasks. One task per iteration.

## A++ STANDARD: Acceptance Criteria Enforcement

**CRITICAL**: A task is NOT complete until ALL acceptance criteria in the task doc are checked off.

Before marking ANY task complete, verify:
1. Read the task doc's **Acceptance Criteria** section
2. EVERY `[ ]` criterion MUST become `[x]`
3. If you only complete SOME criteria, the task stays `[ ]` in PROGRESS.md
4. Update the task doc to show which criteria are done with `[x]`

**Partial implementations are FAILURES.** Do not check off PROGRESS.md until ALL criteria pass.

Example of WRONG behavior:
```
Task has 3 acceptance criteria, you complete 1, mark task done in PROGRESS.md
```

Example of CORRECT behavior:
```
Task has 3 acceptance criteria, you complete 1, task stays [ ] in PROGRESS.md
Next iteration completes criterion 2, task stays [ ] in PROGRESS.md
Next iteration completes criterion 3, NOW mark task [x] in PROGRESS.md
```

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
- `[BUG-048] Fix: Allow negative liquidity values`
- `[TODO-005b] Add: Temporal validation to research workflow`
- `[DEBT-003] Refactor: Add session.begin() transaction boundaries`

## Quality Gates (MUST PASS)

Before marking ANY task complete:
```bash
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

1. **ONE task per iteration**
2. **Read PROGRESS.md first**
3. **Read the task doc (BUG-XXX.md, etc.)**
4. **Verify ALL acceptance criteria are addressed**
5. **Quality gates must pass**
6. **Update task doc acceptance criteria checkboxes**
7. **Mark PROGRESS.md task complete ONLY if ALL criteria done**
8. **Commit before exit**
9. **Exit when done**

## BEFORE EXIT CHECKLIST (MANDATORY)

**You MUST complete ALL of these steps before exiting:**

```bash
# 1. Run ALL quality gates
uv run ruff check .           # Fix any issues
uv run ruff format .          # Auto-format
uv run mypy src/              # Fix type errors
uv run pytest tests/unit -v   # All tests pass

# 2. Verify acceptance criteria
# - Read task doc's Acceptance Criteria section
# - Ensure ALL criteria are [x] checked
# - If any are [ ], do NOT mark PROGRESS.md as complete

# 3. Stage ALL changes (including test files and docs!)
git add -A

# 4. Verify nothing is unstaged
git status  # Should show "nothing to commit" or all staged

# 5. Commit with proper message
git commit -m "$(cat <<'EOF'
[TASK-ID] Brief description

- What was implemented/fixed
- Tests added/updated
- Quality gates passed
EOF
)"
```

**CRITICAL - Do NOT exit if:**

- `git status` shows unstaged changes
- Any quality gate failed
- You haven't committed
- Task doc has unchecked acceptance criteria but PROGRESS.md shows `[x]`

**If quality gates fail:** Fix them, re-run all gates, then commit.

## File Locations

- Bugs: `docs/_bugs/BUG-*.md`
- Debt: `docs/_debt/DEBT-*.md`
- TODOs: `docs/_todo/TODO-*.md`
- Source: `src/kalshi_research/`
- Tests: `tests/unit/`, `tests/integration/`
- Skills: `.claude/skills/kalshi-cli/`

## Task-Specific Guidance

### TODO-005b: Temporal Validation
- Add `TemporalValidator` class to `research/thesis.py`
- Validates that researched events occurred AFTER `market.open_time`
- Add test in `tests/unit/research/test_thesis.py`

### TODO-005c: GOTCHAS Documentation
- Add "Market Timing Trap" section to `.claude/skills/kalshi-cli/GOTCHAS.md`
- Explain that events before `open_time` don't count
- Include the Stranger Things example

### DOCS-001: Sync Task Doc Acceptance Criteria
- Review each task doc in `docs/_bugs/`, `docs/_debt/`, `docs/_todo/`
- Update acceptance criteria checkboxes to match actual implementation state
- This is a documentation-only task (no code changes)

## Completion

When ALL items in PROGRESS.md are checked AND all quality gates pass, exit cleanly.
The loop operator verifies via PROGRESS.md state, not output parsing.

**A++ Standard means:**
- ALL PROGRESS.md items are `[x]`
- ALL task doc acceptance criteria are `[x]`
- ALL quality gates pass
- Clean git working tree
