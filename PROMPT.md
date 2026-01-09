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
3. Complete that ONE item fully (tests pass, quality checks pass)
4. Check off the item: `[ ]` → `[x]`
5. **ATOMIC COMMIT** (see format below)
6. Exit

**DO NOT** attempt multiple tasks. One task per iteration.

## Atomic Commit Format

```bash
git add -A && git commit -m "$(cat <<'EOF'
[TASK-ID] Brief description

- What was implemented/fixed
- Tests added/updated
- Quality gates passed
EOF
)"
```

**Examples:**
- `[BUG-048] Fix: Allow negative liquidity values`
- `[TODO-005] Add: Display open_time in market get`
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
4. **Quality gates must pass**
5. **Mark task complete before exit**
6. **Commit before exit**
7. **Exit when done**

## BEFORE EXIT CHECKLIST (MANDATORY)

**You MUST complete ALL of these steps before exiting:**

```bash
# 1. Run ALL quality gates
uv run ruff check .           # Fix any issues
uv run ruff format .          # Auto-format
uv run mypy src/              # Fix type errors
uv run pytest tests/unit -v   # All tests pass

# 2. Stage ALL changes (including test files!)
git add -A

# 3. Verify nothing is unstaged
git status  # Should show "nothing to commit" or all staged

# 4. Commit with proper message
git commit -m "$(cat <<'EOF'
[TASK-ID] Brief description

- What was implemented/fixed
- Tests added/updated
- Quality gates passed
EOF
)"
```

**⚠️ CRITICAL:** Do NOT exit if:

- `git status` shows unstaged changes
- Any quality gate failed
- You haven't committed

**If quality gates fail:** Fix them, re-run all gates, then commit.

## File Locations

- Bugs: `docs/_bugs/BUG-*.md`
- Debt: `docs/_debt/DEBT-*.md`
- TODOs: `docs/_todo/TODO-*.md`
- Source: `src/kalshi_research/`
- Tests: `tests/unit/`, `tests/integration/`

## Completion

When ALL items in PROGRESS.md are checked AND all quality gates pass, exit cleanly.
The loop operator verifies via PROGRESS.md state, not output parsing.
