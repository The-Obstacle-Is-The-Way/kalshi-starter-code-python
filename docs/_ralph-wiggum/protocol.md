# Ralph Wiggum Loop Protocol

**Created:** 2026-01-06
**Updated:** 2026-01-10
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

### CRITICAL: ANTHROPIC_API_KEY and Billing

**Claude Code billing depends on authentication, NOT on whether you use `-p` (headless) or interactive mode.**

| `ANTHROPIC_API_KEY` in shell? | Claude Code uses... | Cost |
|-------------------------------|---------------------|------|
| **YES** (exported in ~/.zshrc) | API credits | **Pay-per-use** (~$6/day) |
| **NO** (only in .env for Python) | Subscription | **Included in Pro/Max** |

**To use your Pro/Max subscription for Ralph loops:**

```bash
# 1. Check if ANTHROPIC_API_KEY is in your shell environment
env | grep ANTHROPIC_API_KEY

# 2. If found, remove it from ~/.zshrc (or ~/.bashrc)
#    Keep it ONLY in your project's .env file for Python apps

# 3. Verify it's gone (start a new terminal first)
env | grep ANTHROPIC_API_KEY  # Should return nothing

# 4. Now Claude Code will use your subscription!
claude -p "Hello"  # Uses Pro/Max, not API credits
```

**Why this matters:**
- The `.env` file is loaded by Python apps (via `python-dotenv`), NOT by your shell
- Claude Code CLI reads from your **shell environment**
- If you need `ANTHROPIC_API_KEY` for Python apps (like `kalshi agent analyze`), keep it in `.env` only
- This gives you the best of both worlds: free Claude Code + working Python integrations

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

If you don't use a `dev` branch, use `ralph-wiggum-loop` directly off `main` and merge via PR.

### Step 1.5: File Placement (Permanent Root Pattern)

**File locations:**

State files live permanently in root for simplicity:
```
/                           # Project root
├── PROGRESS.md             # State file (permanent)
├── PROMPT.md               # Loop prompt (permanent)
└── docs/_ralph-wiggum/
    └── protocol.md         # This file (reference doc)
```

**Why permanent root?**
- Moving files back and forth is unnecessary friction
- State files need to be read by every iteration
- `.gitignore` can exclude them from certain branches if needed
- No copy/move commands to remember

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

## Work Log

- YYYY-MM-DD: Short entry (what changed + commands run)

---

## Completion Criteria

When ALL boxes are checked, the project is complete.

**Note:** Do NOT include a magic completion phrase here. The loop operator verifies
completion by checking this file's state (all `[x]`), not by parsing output strings.
This prevents reward hacking where the model outputs completion phrases prematurely.
```

### Step 3: Create Prompt File (PROMPT.md)

This is fed to Claude each iteration. Key elements:

```markdown
# Project - Ralph Wiggum Loop Prompt

You are completing [PROJECT]. This prompt runs headless via:

\`\`\`bash
while true; do
  claude --dangerously-skip-permissions -p "$(cat PROMPT.md)"
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
4. **RUN QUALITY GATES** (all must pass)
5. **ATOMIC COMMIT** (see format below)
6. **VERIFY** no unstaged changes remain
7. Exit

**DO NOT** attempt multiple tasks. One task per iteration.
**DO NOT** exit without committing.
**DO NOT** exit with unstaged changes.

## Before Exit Checklist (MANDATORY)

\`\`\`bash
# 1. Run ALL quality gates
uv run ruff check .           # Fix any issues
uv run ruff format .          # Auto-format
uv run mypy src/              # Fix type errors
uv run pytest tests/unit -v   # All tests pass

# 2. Stage ALL changes
git add -A

# 3. Verify nothing unstaged
git status  # Should show all staged or clean

# 4. Commit
git commit -m "[TASK-ID] Brief description"
\`\`\`

**If ANY step fails:** Fix it before exiting. Never exit with failing gates or unstaged changes.

## Atomic Commit Format

\`\`\`bash
git add -A && git commit -m "[TASK-ID] Type: description

- What was done
- Tests added/updated
- Quality gates passed"
\`\`\`

## Quality Gates (MUST PASS)

\`\`\`bash
uv run pre-commit run --all-files
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

When ALL items in PROGRESS.md are checked AND quality gates pass, exit cleanly.

**CRITICAL:** Do not claim completion prematurely. The loop operator verifies
via PROGRESS.md state, not by parsing your output for magic phrases.
```

### Step 3.5: Critical Review Prompt (Mandatory)

Before changing code/docs based on feedback (human reviews, CodeRabbit, another model, your own prior output),
apply this block and validate claims against SSOT:

```text
Review the claim or feedback (it may be from an internal or external agent). Validate every claim from first principles. If—and only if—it’s true and helpful, update the system to align with the SSOT, implemented cleanly and completely (Rob C. Martin discipline). Find and fix all half-measures, reward hacks, and partial fixes if they exist. Be critically adversarial with good intentions for constructive criticism. Ship the exact end-to-end implementation we need.
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
    └── protocol.md        # This file
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

#### Option A (Recommended): Simple YOLO Loop

The original Huntley approach - simple, effective, works anywhere:

```bash
# Navigate to project
cd /path/to/project
git checkout ralph-wiggum-loop

# THE CLASSIC RALPH LOOP
while true; do
  claude --dangerously-skip-permissions -p "$(cat PROMPT.md)"
  sleep 2
done
```

**With iteration limit and state-based completion (recommended):**

```bash
MAX=50
for i in $(seq 1 $MAX); do
  echo "=== Iteration $i/$MAX ==="
  claude --dangerously-skip-permissions -p "$(cat PROMPT.md)"
  # Check state file instead of parsing output (prevents reward hacking)
  if ! grep -q "^\- \[ \]" PROGRESS.md; then
    echo "✅ All tasks complete!"
    break
  fi
  sleep 2
done
```

#### Option B: Granular Permissions (More Conservative)

If you want finer control over what Claude can do:

```bash
MAX=50
for i in $(seq 1 $MAX); do
  echo "=== Iteration $i/$MAX ==="
  claude -p "$(cat PROMPT.md)" \
    --allowedTools "Read,Write,Edit,Glob,Grep,Bash"
  # Check state file instead of parsing output
  if ! grep -q "^\- \[ \]" PROGRESS.md; then
    echo "✅ All tasks complete!"
    break
  fi
  sleep 2
done
```

**Even more restrictive (specific bash commands only):**

```bash
claude -p "$(cat PROMPT.md)" \
  --allowedTools "Read,Write,Edit,Glob,Grep,Bash(git:*),Bash(uv:*),Bash(rg:*)"
```

#### Option C: Claude Code Plugin (In-Session)

If you prefer the official plugin approach:

```bash
cd /path/to/project
git checkout ralph-wiggum-loop
claude  # Start interactive session
```

Then inside Claude Code:
```
/ralph-loop "See PROMPT.md. Follow it exactly." --max-iterations 20
```

To cancel: `/cancel-ralph`

**Note:** Plugin state lives in `.claude/ralph-loop.local.md`.

**⚠️ Warning:** The plugin supports `--completion-promise` flags, but we recommend
against using them. Rely on state-file verification instead to prevent reward hacking.

#### Option D: Convenience Script (Recommended for This Repo)

This repo includes a ready-to-use script at `scripts/ralph-loop.sh`:

```bash
# Start in tmux (recommended)
tmux new -s ralph
./scripts/ralph-loop.sh
```

Or start it directly in a background tmux session:

```bash
# Kill any existing session and start fresh
tmux kill-session -t ralph 2>/dev/null
tmux new-session -d -s ralph "./scripts/ralph-loop.sh"

# Attach to watch
tmux attach -t ralph
```

**Script location:** `scripts/ralph-loop.sh`

---

### Claude Code CLI Reference

**Verified from [official docs](https://code.claude.com/docs/en/headless):**

| Flag | Description |
|------|-------------|
| `-p, --print` | Run non-interactively (headless mode) |
| `--dangerously-skip-permissions` | Skip ALL permission prompts (YOLO mode) |
| `--allowedTools "Read,Edit,Bash"` | Auto-approve specific tools |
| `--allowedTools "Bash(git:*)"` | Pattern match specific commands |
| `--disallowedTools "Bash(rm:*)"` | Block specific tools/commands |
| `--output-format text\|json\|stream-json` | Control output format |
| `--continue` | Continue most recent conversation |
| `--resume <session_id>` | Resume specific session |
| `--append-system-prompt "..."` | Add to system prompt |

**About `--dangerously-skip-permissions`:**
- Works ANYWHERE (not just Docker) - the Docker recommendation is for **safety**, not functionality
- Anthropic recommends Docker isolation to prevent data loss/exfiltration
- For Ralph loops in a **sandboxed git branch**, this is acceptable risk
- Your safety net is `git reset --hard` or deleting the branch

### Stop Conditions

Your loop should stop when:
1. **Iteration limit reached** - Always set `MAX` in your loop
2. **All tasks complete** - Check `PROGRESS.md` for all `[x]` markers
3. **Manual intervention** - Ctrl+C when you're satisfied

**IMPORTANT: Avoid magic completion phrases entirely.**

Do NOT instruct the model to output phrases like "PROJECT COMPLETE" or use XML tags
like `<promise>...</promise>`. This creates reward hacking risk where the model
outputs the phrase prematurely to exit the loop.

**Instead, verify completion via state:**
```bash
# Check if all tasks are marked complete
if ! grep -q "^\- \[ \]" PROGRESS.md; then
  echo "✅ All tasks complete"
  break
fi
```

This verifies actual progress (checked boxes) rather than trusting model output.

### Safety Philosophy

**Your real safety net is the sandboxed branch:**
- All work happens on `ralph-wiggum-loop` (or similar)
- Main branch is untouched
- You can always `git checkout main && git branch -D ralph-wiggum-loop`
- Audit commits before merging

**Tool restrictions are optional paranoia.** If you're in a sandboxed branch:
- `--dangerously-skip-permissions` is fine
- Blocking `rm` would break legitimate cleanup operations
- The worst case is you delete the branch and start over

**When to use granular permissions:**
- Running on production systems (don't do Ralph on prod)
- Shared environments where mistakes affect others
- When you don't trust your prompt/specs

### Rate Limits

- The `sleep 2` between iterations helps avoid rate limits
- If you hit limits, increase sleep or add exponential backoff
- If the same failure repeats 3+ times, stop and fix the prompt

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

- ✅ Always sandbox in dedicated branch (this is your real safety)
- ✅ Use detailed specs for each task
- ✅ Require atomic commits
- ✅ Set clear completion criteria
- ✅ Set iteration limits (`MAX=50` or similar)
- ✅ Keep the prompt focused and stable
- ✅ Monitor periodically
- ✅ Audit before merging

### DON'T

- ❌ Run on main branch (use a sandbox branch!)
- ❌ Skip the state file (PROGRESS.md is the brain)
- ❌ Allow multi-task iterations (one task = one iteration)
- ❌ Trust without auditing
- ❌ Use vague task descriptions
- ❌ Run without iteration limits (infinite loops burn money)

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

Use `--dangerously-skip-permissions` to bypass all prompts:
```bash
claude --dangerously-skip-permissions -p "$(cat PROMPT.md)"
```

Or use `--allowedTools` for granular control:
```bash
claude -p "$(cat PROMPT.md)" --allowedTools "Read,Write,Edit,Bash"
```

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
# 1. Create sandbox branch
git checkout dev && git pull
git checkout -b ralph-wiggum-cleanup

# 2. Ensure PROGRESS.md and PROMPT.md exist in root
# (They should already be there - permanent location)
ls PROGRESS.md PROMPT.md

# 3. Ensure spec docs exist for each task (docs/_bugs/, docs/_debt/, docs/_specs/, docs/_future/)

# 4. Start tmux
tmux new -s ralph

# 5. Run the loop (state-based completion check):
MAX=50; for i in $(seq 1 $MAX); do
  echo "=== Iteration $i/$MAX ==="
  claude --dangerously-skip-permissions -p "$(cat PROMPT.md)"
  # Check if all tasks complete (no unchecked boxes)
  if ! grep -q "^\- \[ \]" PROGRESS.md; then
    echo "✅ All tasks complete"
    break
  fi
  sleep 2
done

# 6. Monitor in another pane (optional)
watch -n 5 'git log --oneline -10'

# 7. Audit when done
git log dev..ralph-wiggum-cleanup --oneline
git diff dev..ralph-wiggum-cleanup --stat

# 8. Merge if good (after review)
git checkout dev && git merge ralph-wiggum-cleanup
# Or open PR for review
```
