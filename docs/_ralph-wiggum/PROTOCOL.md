# Ralph Wiggum Loop Protocol

**Created:** 2026-01-06
**Updated:** 2026-01-07
**Author:** Ray + Claude
**Status:** Tested & Working

---

## What is the Ralph Wiggum Technique?

The Ralph Wiggum technique (popularized by Geoffrey Huntley) is an iterative AI development methodology where the **same prompt is run repeatedly** until objective completion criteria are met. The "self-referential" part is that each iteration sees its **previous work in files and git history**, not that model output is fed back as input.

There are two common implementations:

1. **External process loop (fresh context)**: a bash `while` loop runs a new `claude -p` process each iteration. Each run starts with empty conversational context and relies on state files + the repo.
2. **In-session stop-hook loop (persistent context)**: Claude Code’s official `ralph-loop` plugin uses a Stop hook to block exits and re-feed the same prompt inside a single session.

### Why It Works

- **Same prompt, repeated** = Iteration beats one-shot perfection
- **State tracked in files** = Progress persists across iterations
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

# jq (required by Claude Code ralph-loop stop hook)
brew install jq    # macOS
apt install jq     # Linux

# uv (Python package manager) - if doing Python work
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Project Requirements

1. **State file** (e.g., `PROGRESS.md`) - Tracks what's done/pending
2. **Prompt file** (e.g., `PROMPT.md`) - Instructions for each iteration
3. **Specs/Bugs docs** - Detailed requirements for each task
4. **Git repo** - For atomic commits and history
5. **Scratchpad dir** (e.g., `.agent/`) - Long-term plan/logs without bloating the prompt

---

## Setup Protocol

### Step 1: Create Branch Structure

**CRITICAL:** Always sandbox Ralph work in a dedicated branch.

```bash
# Start from main
git checkout main
git pull origin main

# Optional: create dev branch (integration branch)
git checkout -b dev  # optional

# Create Ralph branch (all autonomous work happens here)
git checkout -b ralph-wiggum-loop  # if you skipped dev, create this off main

# Push branches to remote for backup
git push -u origin dev  # optional
git push -u origin ralph-wiggum-loop
```

**Branch hierarchy (recommended):**
```
main (protected, production)
  └── dev (integration, manual merges)
        └── ralph-wiggum-loop (autonomous work)
```

If you don’t use a `dev` branch, use `ralph-wiggum-loop` directly off `main` and merge via PR.

### Step 2: Create State File (PROGRESS.md)

This is the **brain** of the loop. Each iteration reads this to find the next task.

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

This is fed to Claude each iteration (external loop), or used as the input prompt for `/ralph-loop` (plugin loop). Key elements:

```markdown
# Project - Ralph Wiggum Loop Prompt

You are completing [PROJECT]. This prompt runs headless via:

\`\`\`bash
while true; do
  cat PROMPT.md | claude -p --allowedTools "Read Write Edit Glob Grep Bash(git* uv* rg* cat* ls* mkdir*)"
  sleep 2
done
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

Inside tmux, choose ONE of these approaches:

#### Option A (Recommended): Claude Code `ralph-loop` plugin (Stop hook, in-session)

This avoids external bash loops and provides built-in iteration limits.

1. Start Claude Code normally:
   ```bash
   cd /path/to/project
   git checkout ralph-wiggum-loop
   claude
   ```

2. Install the plugin (once per environment):
   ```
   /plugin install ralph-loop@claude-plugin-directory
   ```

3. Start the loop in your session:
   ```
   /ralph-loop "See PROMPT.md. Follow it exactly." --max-iterations 20 --completion-promise "PROJECT COMPLETE"
   ```

The loop advances when Claude tries to exit: the Stop hook blocks the exit and re-feeds the same prompt for the next iteration. Plugin state lives in `.claude/ralph-loop.local.md` (removed by `/cancel-ralph`).

To cancel:
```
/cancel-ralph
```

#### Option B: External bash loop (fresh `claude -p` process each iteration)

This matches the “run Claude headlessly in a loop” style used in many writeups.

```bash
# Navigate to project
cd /path/to/project

# Ensure on ralph branch
git checkout ralph-wiggum-loop

# Recommended: add a hard safety limit
MAX_ITERS=50
PROMISE="PROJECT COMPLETE"

mkdir -p .claude
for i in $(seq 1 "$MAX_ITERS"); do
  echo "=== Ralph iteration $i/$MAX_ITERS ===" | tee -a .claude/ralph.log
  cat PROMPT.md | claude -p \
    --output-format text \
    --allowedTools "Read Write Edit Glob Grep Bash(git* uv* rg* cat* ls* mkdir*)" \
    --disallowedTools "Bash(rm* sudo* pkill* kill* shutdown* reboot* dd* mkfs*)" \
    | tee -a .claude/ralph.log

  if grep -Fq "<promise>${PROMISE}</promise>" .claude/ralph.log; then
    echo "✅ Detected completion promise: <promise>${PROMISE}</promise>" | tee -a .claude/ralph.log
    break
  fi

  sleep 2
done
```

**Claude Code CLI flags (verified via `claude --help`, Claude Code v0.2.115):**
- `-p, --print` prints the response and exits (required for headless loops).
- `--output-format text|json|stream-json` works only with `--print` and enables machine parsing.
- `--allowedTools` / `--disallowedTools` are the intended non-interactive tool allow/deny lists (supports `Bash(git*)`-style patterns).
- `--system-prompt` can harden guardrails (only works with `--print`).
- `--dangerously-skip-permissions` exists, but the CLI currently states it “Only works in Docker containers with no internet access.” Treat it as non-portable.

### Stop Conditions (Don’t run forever)

- Always set an iteration cap: `--max-iterations` (plugin) or `MAX_ITERS` (bash loop).
- Treat `<promise>...</promise>` as a mechanical stop signal, not proof of correctness; require tests/linters/type checks to pass before allowing the promise.
- Keep the promise text short, unique, and used only in the final “Completion” section to avoid accidental matches.

### Tool Permission Hardening

- Prefer `--allowedTools` with Bash patterns (e.g., `Bash(git* uv* rg* cat* ls*)`) and explicitly deny destructive patterns via `--disallowedTools` (e.g., `Bash(rm* sudo* pkill* kill* shutdown* reboot* dd* mkfs*)`).
- Avoid giving broad execution primitives (`python`, `node`) unless you need them; prefer project runners like `uv run ...`.
- Real-world gotcha: autonomous loops have been observed to self-terminate via `pkill` when “stuck” — disallow process-kill tools unless you truly want that behavior.

### Rate Limits & Recovery

- Add `sleep` and consider exponential backoff when you see rate-limit errors.
- If you see the same failing output repeat N iterations, stop the loop and revise the prompt/spec instead of burning more iterations.

---

## Monitoring

### Watch Progress

```bash
# In another terminal/tmux pane
watch -n 5 'head -50 PROGRESS.md'

# Or check git activity
watch -n 5 'git log --oneline -10'
```

Note: `watch` is not installed by default on macOS. Use `brew install watch` or replace with a small `while true; do ...; sleep 5; done` loop.

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

If you skipped `dev`, open a PR from `ralph-wiggum-loop` → `main`, or merge directly after review.

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
- ✅ Prefer iteration limits (`--max-iterations` / `MAX_ITERS`)
- ✅ Keep the prompt short and stable
- ✅ Restrict tool permissions (especially `Bash(...)`)
- ✅ Monitor periodically
- ✅ Audit before merging

### DON'T

- ❌ Run on main branch
- ❌ Skip the state file
- ❌ Allow multi-task iterations
- ❌ Commit broken code repeatedly (future iterations compound failures)
- ❌ Give unrestricted Bash (agents will eventually do something unsafe)
- ❌ Trust without auditing
- ❌ Use vague task descriptions

### Prompt Tuning Tips

1. **Be explicit** - Claude follows instructions literally
2. **One task rule** - Prevents context overload
3. **Quality gates** - Catch issues early
4. **Read first** - Always read state before acting
5. **Atomic commits** - Easy rollback if needed
6. **Escape hatch** - If stuck after N tries, require a blocking report + stop

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

1. **Fresh context can work** - External loops start clean and reduce drift
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

### Permission Prompts Block Autonomy

1. Prefer `/ralph-loop` (plugin loop) or use `--allowedTools` / `--disallowedTools`.
2. Accept Claude Code trust prompts interactively once if required (then re-run headless).
3. Do not rely on `--dangerously-skip-permissions` unless you’re in an environment where it’s documented to work.

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
- [Anthropic Claude Code Plugins Directory](https://github.com/anthropics/claude-plugins-official)
- [Anthropic `ralph-loop` plugin](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/ralph-loop)
- [RepoMirror field report: “We Put a Coding Agent in a While Loop…”](https://github.com/repomirrorhq/repomirror/blob/main/repomirror.md)
- [Ralph Orchestrator](https://github.com/mikeyobrien/ralph-orchestrator)
- [Ralph for Claude Code (community, adds rate limits/circuit breakers)](https://github.com/frankbria/ralph-claude-code)
- [Claude Code documentation](https://code.claude.com/docs/en/)
- [Claude Code plugins documentation](https://code.claude.com/docs/en/plugins)

---

## Quick Start Checklist

```bash
# 1. Branch (recommended: work in a sandbox branch)
git checkout -b ralph-wiggum-loop  # or: git checkout -b dev && git checkout -b ralph-wiggum-loop

# 2. Create PROGRESS.md with [ ] tasks

# 3. Create PROMPT.md with instructions

# 4. Create spec docs for each task

# 5. Start tmux
tmux new -s ralph

# 6a. Recommended: use Claude Code plugin (run `claude`, then inside it:)
# /plugin install ralph-loop@claude-plugin-directory
# /ralph-loop "See PROMPT.md. Follow it exactly." --max-iterations 20 --completion-promise "PROJECT COMPLETE"

# 6b. Or run an external loop (fresh process each iteration, with a limit)
MAX_ITERS=50 PROMISE="PROJECT COMPLETE" bash -lc '
  mkdir -p .claude
  for i in $(seq 1 "$MAX_ITERS"); do
    cat PROMPT.md | claude -p --allowedTools "Read Write Edit Glob Grep Bash(git* uv* rg* cat* ls* mkdir*)" --disallowedTools "Bash(rm* sudo* pkill* kill* shutdown* reboot* dd* mkfs*)" | tee -a .claude/ralph.log
    grep -Fq "<promise>${PROMISE}</promise>" .claude/ralph.log && break
    sleep 2
  done
'

# 7. Monitor in another pane
watch -n 5 'git log --oneline -10'

# 8. Audit when done
git log main..ralph-wiggum-loop

# 9. Merge if good (prefer PR review)
# If using dev:
#   git checkout dev && git merge ralph-wiggum-loop
#   git checkout main && git merge dev
# Otherwise:
#   PR: ralph-wiggum-loop -> main
```
