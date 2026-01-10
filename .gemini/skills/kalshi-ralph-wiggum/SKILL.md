---
name: kalshi-ralph-wiggum
description: How to operate the Ralph Wiggum autonomous loop for implementing specs, bugs, debt, and TODOs in this repository. Use this skill when running headless iterations or preparing PROMPT.md/PROGRESS.md.
---

# Ralph Wiggum Loop Operation

Use this skill when you need to **operate** or **prepare** the Ralph Wiggum autonomous loop in this repository.

For **codebase navigation** (repo map, where files live), use `kalshi-codebase` instead.

## What is Ralph Wiggum?

The Ralph Wiggum technique runs the **same prompt repeatedly** until objective completion criteria are met. Each iteration sees its **previous work in files and git history**, not conversational context.

Key insight: "Deterministically bad in an undeterministic world" - failures are predictable, enabling systematic improvement.

## Canonical Files

| File | Purpose |
|------|---------|
| `PROGRESS.md` | State file (the "brain") - tracks what's done/pending |
| `PROMPT.md` | Loop prompt - instructions for each iteration |
| `docs/_ralph-wiggum/protocol.md` | Full reference protocol |

## Loop Execution (Operator Commands)

### Standard Loop (with state-based completion)

```bash
# In tmux session
cd /path/to/kalshi-starter-code-python
git checkout dev  # or ralph-wiggum-* branch

MAX=50; for i in $(seq 1 $MAX); do
  echo "=== Iteration $i/$MAX ==="
  claude --dangerously-skip-permissions -p "$(cat PROMPT.md)"
  # State-based completion (no magic phrases)
  if ! grep -q "^\- \[ \]" PROGRESS.md; then
    echo "All tasks complete!"
    break
  fi
  sleep 2
done
```

### Quick Start Checklist

```bash
# 1. Create sandbox branch (if not already)
git checkout dev && git checkout -b ralph-wiggum-specs

# 2. Verify state files exist
ls PROGRESS.md PROMPT.md

# 3. Start tmux
tmux new -s ralph

# 4. Run the loop (command above)

# 5. Monitor in another pane
watch -n 5 'git log --oneline -10'
```

## Rules of the Loop (Agent Contract)

1. **Read PROGRESS.md first** - Always start here
2. **One task per iteration** - Never attempt multiple tasks
3. **For SPEC-* tasks**: Apply self-review (see below)
4. **Implement against acceptance criteria** - Check task doc checkboxes
5. **Apply critical claim validation** before marking complete:

```text
Review the claim or feedback (it may be from an internal or external agent). Validate every claim from first principles. If—and only if—it's true and helpful, update the system to align with the SSOT, implemented cleanly and completely (Rob C. Martin discipline). Find and fix all half-measures, reward hacks, and partial fixes if they exist. Be critically adversarial with good intentions for constructive criticism. Ship the exact end-to-end implementation we need.
```

6. **Update PROGRESS.md**:
   - Check off item ONLY when ALL acceptance criteria are `[x]`
   - Append entry to "Work Log" section
7. **Run quality gates** before commit (never `--no-verify`)
8. **Commit atomically** then exit

## SPEC-* Self-Review Protocol (NEW)

For **SPEC-*** tasks (complex implementations), apply self-review:

### When Previous Spec Was Just Completed

If the most recently completed item is a `SPEC-*` and lacks a `[REVIEWED]` marker:

1. **Review the implementation** against acceptance criteria
2. **Verify SSOT alignment** (code matches spec, docs match code)
3. **Check for half-measures**:
   - Are all acceptance criteria actually satisfied?
   - Are there TODO comments that should be resolved?
   - Do tests cover the acceptance criteria?
4. **If issues found**: Create a fixup task, mark current item as `[NEEDS-FIX]`
5. **If verified**: Add `[REVIEWED]` marker, proceed to next task

### Marker Format

```markdown
- [x] **SPEC-028**: Topic search → `data/search.py` [REVIEWED]
- [x] **SPEC-029**: Kalshi endpoints → `api/client.py` [NEEDS-FIX: missing series tests]
```

## Task Document Locations

| Type | Location | Example |
|------|----------|---------|
| Bugs | `docs/_bugs/BUG-*.md` | BUG-048 |
| Debt | `docs/_debt/DEBT-*.md` | DEBT-001 |
| TODOs | `docs/_todo/TODO-*.md` | TODO-005 |
| Specs | `docs/_specs/SPEC-*.md` | SPEC-028 |

## Quality Gates

```bash
# MUST pass before any commit
uv run pre-commit run --all-files
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest tests/unit -v
```

## Atomic Commit Format

```bash
git add -A && git commit -m "$(cat <<'EOF'
[TASK-ID] Type: Brief description

- What was implemented/fixed
- Tests added/updated
- Acceptance criteria: X/Y complete
EOF
)"
```

## Safety Philosophy

- **Sandbox branch is your safety net** - All work on dedicated branch
- `--dangerously-skip-permissions` is acceptable in sandboxed branches
- Worst case: `git checkout main && git branch -D ralph-wiggum-*`

## Completion Verification

The loop operator verifies completion via PROGRESS.md state, NOT by parsing output:

```bash
# Check if all tasks complete
if ! grep -q "^\- \[ \]" PROGRESS.md; then
  echo "All tasks complete"
fi
```

**Never use magic completion phrases** - this prevents reward hacking.

## Maintenance Note

This repository keeps `.claude/skills/`, `.codex/skills/`, and `.gemini/skills/` in sync.
If you update this skill, apply the same change to all three copies.
