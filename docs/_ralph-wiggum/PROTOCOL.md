# Ralph Wiggum Loop Protocol

**Created:** 2026-01-06
**Author:** Ray + Claude
**Status:** Tested & Working

---

## What is the Ralph Wiggum Technique?

The Ralph Wiggum technique (pioneered by Geoffrey Huntley) is an iterative AI development methodology where the **same prompt is fed to Claude repeatedly** in a bash loop. Each iteration:

1. Spawns a **fresh Claude instance** with clean context
2. Claude reads state files to understand what's done
3. Completes **ONE task**
4. Commits changes
5. Exits
6. Loop restarts → repeat

The "self-referential" aspect comes from Claude seeing its **previous work in files and git history**, not from feeding output back as input.

### Why It Works

- **Fresh context each iteration** = No accumulated confusion
- **State tracked in files** = Persistent progress across iterations
- **Atomic commits** = Easy to audit, revert, or cherry-pick
- **Sandboxed branch** = Safe experimentation

### Key Quote

> "Deterministically bad in an undeterministic world" - failures are predictable, enabling systematic improvement through prompt tuning.

---

## Prerequisites

### Tools Required

```bash
# Claude Code CLI
npm install -g @anthropic-ai/claude-code

# tmux (for persistent sessions)
brew install tmux  # macOS
apt install tmux   # Linux

# uv (Python package manager) - if doing Python work
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Project Requirements

1. **State file** (e.g., `PROGRESS.md`) - Tracks what's done/pending
2. **Prompt file** (e.g., `PROMPT.md`) - Instructions for each iteration
3. **Specs/Bugs docs** - Detailed requirements for each task
4. **Git repo** - For atomic commits and history

---

## Setup Protocol

### Step 1: Create Branch Structure

**CRITICAL:** Always sandbox Ralph work in a dedicated branch.

```bash
# Start from main
git checkout main
git pull origin main

# Create dev branch (integration branch)
git checkout -b dev

# Create Ralph branch (all autonomous work happens here)
git checkout -b ralph-wiggum-loop

# Push branches to remote for backup
git push -u origin dev
git push -u origin ralph-wiggum-loop
```

**Branch hierarchy:**
```
main (protected, production)
  └── dev (integration, manual merges)
        └── ralph-wiggum-loop (autonomous work)
```

### Step 2: Create State File (PROGRESS.md)

This is the **brain** of the loop. Each fresh Claude reads this to find the next task.

```markdown
# Project Name - Progress Tracker

**Last Updated:** YYYY-MM-DD
**Purpose:** State file for Ralph Wiggum loop

---

## Phase 1: Critical Fixes

- [ ] **BUG-001**: Description → See `docs/_bugs/BUG-001.md`
- [ ] **BUG-002**: Description → See `docs/_bugs/BUG-002.md`

## Phase 2: Features

- [ ] **SPEC-001**: Description → See `docs/_specs/SPEC-001.md`
- [ ] **SPEC-002**: Description → See `docs/_specs/SPEC-002.md`

## Phase 3: Verification

- [ ] **FINAL-001**: All tests pass
- [ ] **FINAL-002**: All quality gates pass

---

## Completion Criteria

When ALL boxes are checked:

\`\`\`
<promise>PROJECT COMPLETE</promise>
\`\`\`
```

### Step 3: Create Prompt File (PROMPT.md)

This is fed to Claude each iteration. Key elements:

```markdown
# Project - Ralph Wiggum Loop Prompt

You are completing [PROJECT]. This prompt runs headless via:

\`\`\`bash
while true; do claude --dangerously-skip-permissions -p "$(cat PROMPT.md)"; sleep 2; done
\`\`\`

## First Action: Read State

**IMMEDIATELY** read state files:
\`\`\`bash
cat PROGRESS.md
cat docs/_bugs/README.md
\`\`\`

## Your Task This Iteration

1. Find the **FIRST** unchecked `[ ]` item in PROGRESS.md
2. Complete that ONE item fully
3. Check off the item: `[ ]` → `[x]`
4. **ATOMIC COMMIT** (see format below)
5. Exit

**DO NOT** attempt multiple tasks. One task per iteration.

## Atomic Commit Format

\`\`\`bash
git add -A && git commit -m "[TASK-ID] Type: description

- What was done
- Tests added/updated
- Quality gates passed"
\`\`\`

## Quality Gates (MUST PASS)

\`\`\`bash
uv run ruff check .           # Lint
uv run ruff format --check .  # Format
uv run mypy src/              # Types
uv run pytest tests/ -v       # Tests
\`\`\`

## Guardrails

1. ONE task per iteration
2. Tests first (TDD)
3. Quality gates must pass
4. Read PROGRESS.md first
5. Mark task complete before exit
6. Commit before exit
7. Follow specs exactly

## Completion

When ALL items checked AND quality gates pass:

\`\`\`
<promise>PROJECT COMPLETE</promise>
\`\`\`

**CRITICAL:** Only output this when TRUE. Do not lie to exit.
```

### Step 4: Create Spec/Bug Docs

Each task should have a detailed spec:

```
docs/
├── _bugs/
│   ├── README.md          # Summary of all bugs
│   ├── BUG-001.md         # Detailed bug description
│   └── BUG-002.md
├── _specs/
│   ├── README.md          # Summary of all specs
│   ├── SPEC-001.md        # Detailed spec
│   └── SPEC-002.md
└── _ralph-wiggum/
    └── PROTOCOL.md        # This file
```

### Step 5: Start tmux Session

```bash
# Create named session
tmux new-session -s ralph

# Or attach to existing
tmux attach -t ralph

# Detach without killing: Ctrl+B, then D
# Kill session: tmux kill-session -t ralph
```

### Step 6: Run the Loop

Inside tmux:

```bash
# Navigate to project
cd /path/to/project

# Ensure on ralph branch
git checkout ralph-wiggum-loop

# THE MAGIC COMMAND
while true; do
  claude --dangerously-skip-permissions -p "$(cat PROMPT.md)"
  sleep 2
done
```

**Flags explained:**
- `--dangerously-skip-permissions` - No interactive prompts (fully autonomous)
- `-p "$(cat PROMPT.md)"` - Run in headless mode with prompt from file

---

## Monitoring

### Watch Progress

```bash
# In another terminal/tmux pane
watch -n 5 'head -50 PROGRESS.md'

# Or check git activity
watch -n 5 'git log --oneline -10'
```

### Check Loop Status

```bash
# See recent commits
git log --oneline -20

# See what changed
git diff HEAD~1

# Check test status
uv run pytest tests/ -v --tb=short
```

---

## Post-Loop Audit

### Review All Changes

```bash
# See all commits from Ralph
git log main..ralph-wiggum-loop --oneline

# See full diff
git diff main..ralph-wiggum-loop

# Review specific commit
git show <commit-hash>
```

### Run Quality Gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest tests/ -v
```

### Merge if Good

```bash
# If everything looks good
git checkout dev
git merge ralph-wiggum-loop
git checkout main
git merge dev
git push origin main
```

### Revert if Bad

```bash
# Nuclear option - delete branch entirely
git checkout main
git branch -D ralph-wiggum-loop

# Or revert specific commits
git revert <bad-commit-hash>
```

---

## Best Practices

### DO

- ✅ Always sandbox in dedicated branch
- ✅ Use detailed specs for each task
- ✅ Require atomic commits
- ✅ Set clear completion criteria
- ✅ Monitor periodically
- ✅ Audit before merging

### DON'T

- ❌ Run on main branch
- ❌ Skip the state file
- ❌ Allow multi-task iterations
- ❌ Trust without auditing
- ❌ Use vague task descriptions

### Prompt Tuning Tips

1. **Be explicit** - Claude follows instructions literally
2. **One task rule** - Prevents context overload
3. **Quality gates** - Catch issues early
4. **Read first** - Always read state before acting
5. **Atomic commits** - Easy rollback if needed

---

## Example: Kalshi Research Platform

This protocol was used to build the Kalshi prediction market research platform.

### Initial State
- Core platform built (SPEC-001 through SPEC-004)
- 185 tests passing, 81% coverage
- Several bugs and features remaining

### Ralph Loop Results

| Commit | Task | Time |
|--------|------|------|
| `9e4e55e` | BUG-007: Fix CI/CD | ~2 min |
| `7a03b97` | QUALITY-001: Fix mypy error | ~1 min |
| `8f9da97` | QUALITY-002: Fix ruff issues | ~1 min |
| `5b3ab7c` | QUALITY-003: Verify gates | ~1 min |
| `394719f` | SPEC-005: Alerts module | ~5 min |
| `9feab0e` | SPEC-006: Correlation analysis | ~5 min |
| `9ecefc6` | SPEC-007: Visualization | ~5 min |
| ... | SPEC-008, FINAL-* | ongoing |

### Files Created

```
PROMPT.md           # Loop prompt
PROGRESS.md         # State tracking
docs/_bugs/         # Bug documentation
docs/_specs/        # Spec documentation
docs/_ralph-wiggum/ # This protocol
```

### Key Learnings

1. **Fresh context works** - Each iteration starts clean, no confusion
2. **State files are critical** - PROGRESS.md is the brain
3. **Atomic commits enable auditing** - Easy to review each change
4. **Sandboxing is essential** - Never risk main branch
5. **TDD keeps quality high** - Tests catch regressions

---

## Troubleshooting

### Loop Stops Unexpectedly

```bash
# Check if Claude is running
ps aux | grep claude

# Check tmux session
tmux list-sessions

# Restart loop
tmux attach -t ralph
# Then re-run the while loop
```

### Claude Gets Stuck

1. Check PROGRESS.md for unclear tasks
2. Add more detail to the spec doc
3. Kill current iteration (Ctrl+C)
4. Loop will restart with fresh context

### Quality Gates Failing

- Loop should auto-fix on next iteration
- If persistent, check the spec for issues
- May need to manually intervene

### Merge Conflicts

```bash
# On ralph branch
git fetch origin
git rebase origin/main
# Resolve conflicts
git rebase --continue
```

---

## References

- [Geoffrey Huntley - Ralph Wiggum](https://ghuntley.com/ralph/)
- [Ralph Orchestrator](https://github.com/mikeyobrien/ralph-orchestrator)
- [Claude Code CLI](https://docs.anthropic.com/claude-code)

---

## Quick Start Checklist

```bash
# 1. Branch
git checkout -b ralph-wiggum-loop

# 2. Create PROGRESS.md with [ ] tasks

# 3. Create PROMPT.md with instructions

# 4. Create spec docs for each task

# 5. Start tmux
tmux new -s ralph

# 6. Run loop
while true; do claude --dangerously-skip-permissions -p "$(cat PROMPT.md)"; sleep 2; done

# 7. Monitor in another pane
watch -n 5 'git log --oneline -10'

# 8. Audit when done
git log main..ralph-wiggum-loop

# 9. Merge if good
git checkout main && git merge ralph-wiggum-loop
```
