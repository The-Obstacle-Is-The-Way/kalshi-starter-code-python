# Kalshi Research Platform - Ralph Wiggum Loop Prompt

You are completing a Kalshi prediction market research platform. This prompt is designed for headless execution via:

```bash
while true; do claude -p "$(cat PROMPT.md)" --allowedTools "Bash,Read,Write,Edit,Glob,Grep"; done
```

## First Action: Read State

**IMMEDIATELY** read `PROGRESS.md` to see what's done:
```bash
cat PROGRESS.md
```

Then read the bug tracker:
```bash
cat docs/_bugs/README.md
```

## Your Task This Iteration

1. Find the **FIRST** unchecked item in `PROGRESS.md`
2. Complete that ONE item fully (tests pass, quality checks pass)
3. Check off the item in `PROGRESS.md`
4. Commit your changes
5. Exit

**DO NOT** attempt multiple tasks. One task per iteration. Exit when done.

## TDD Workflow (MANDATORY)

For EVERY code change, follow RED-GREEN-REFACTOR:

### RED: Write failing test first
```bash
# Create/update test file BEFORE implementation
uv run pytest tests/unit/test_<module>.py -v -k "test_name"  # Should FAIL
```

### GREEN: Write minimal code to pass
```bash
uv run pytest tests/unit/test_<module>.py -v -k "test_name"  # Should PASS
```

### REFACTOR: Clean up, keep tests green
```bash
uv run ruff check . --fix && uv run ruff format .
uv run mypy src/
uv run pytest tests/unit -v  # Still passes
```

## Quality Gates (MUST PASS)

Before marking ANY task complete, ALL of these must pass:
```bash
uv run ruff check .           # No lint errors
uv run ruff format --check .  # Properly formatted
uv run mypy src/              # No type errors
uv run pytest tests/unit -v   # All tests pass
```

If ANY check fails, fix it before proceeding. No exceptions.

## Testing Philosophy

**ONLY mock at system boundaries:**
- HTTP calls to external APIs → use `respx`
- File system → use `tmp_path` fixture

**NEVER mock:**
- Your own domain objects (Market, Trade, etc.)
- Pydantic models - use REAL instances
- Pure functions - test with real data
- Repositories - use real in-memory SQLite

## Commit Format

After completing a task:
```bash
git add -A
git commit -m "Fix BUG-XXX: <description>"
# or
git commit -m "Implement SPEC-XXX: <description>"
```

## Guardrails (DO NOT VIOLATE)

1. **ONE task per iteration** - Do not attempt multiple tasks
2. **Tests first** - Never write implementation before tests
3. **Quality gates must pass** - No exceptions
4. **Read PROGRESS.md first** - Always check state before working
5. **Mark task complete** - Update PROGRESS.md before exiting
6. **Commit before exit** - Always commit your work
7. **No breaking changes** - Existing tests must still pass
8. **Follow specs exactly** - Read `docs/_specs/SPEC-XXX.md` before implementing
9. **Read bug docs** - Read `docs/_bugs/BUG-XXX.md` before fixing
10. **Exit when done** - Don't start another task in the same iteration

## File Locations

- Specs: `docs/_specs/SPEC-*.md`
- Bugs: `docs/_bugs/BUG-*.md`
- Progress: `PROGRESS.md`
- Source: `src/kalshi_research/`
- Tests: `tests/unit/`, `tests/integration/`

## Current Project State

The core platform (SPEC-001 through SPEC-004) is mostly implemented:
- 185 unit tests passing
- ~81% coverage
- ruff/mypy mostly passing (1 minor type issue)

Remaining work tracked in `PROGRESS.md`.

## Completion

When ALL items in `PROGRESS.md` are checked AND all quality gates pass:

```
<promise>KALSHI RESEARCH PLATFORM COMPLETE</promise>
```

**CRITICAL:** Only output this promise when it is TRUE. Do not lie to exit the loop.
