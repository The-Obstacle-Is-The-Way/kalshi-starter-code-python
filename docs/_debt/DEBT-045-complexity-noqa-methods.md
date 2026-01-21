# DEBT-045: Complexity — Remove `# noqa: PLR0912/PLR0915` Methods

## Status

- **Severity:** HIGH
- **Effort:** M (1–3 days)
- **Blocking:** Yes (these functions are change magnets)
- **Target Date:** 2026-02-05
- **Status:** Resolved

## Problem

There are functions that explicitly disable Ruff complexity rules (`PLR0912`/`PLR0915`).
This is not a solution — it’s a confession that the code is too complex to safely change.

## Evidence

Reproduce:

```bash
rg -n \"noqa: PLR091\" src/kalshi_research
```

Current offenders (2026-01-19 audit):

```text
src/kalshi_research/agent/research_agent.py:_execute_research_task 313-459 (147 lines)
src/kalshi_research/execution/executor.py:_run_live_checks 231-351 (121 lines)
src/kalshi_research/cli/agent.py:research 19-175 (157 lines)
src/kalshi_research/cli/agent.py:analyze 179-372 (194 lines)
src/kalshi_research/cli/research.py:research_thesis_show 433-559 (127 lines)
src/kalshi_research/cli/scan.py:scan_movers 1156-1304 (149 lines)
```

## Solution (Decompose Until Readable)

### Target rule

- No function > ~40 lines unless it is a pure formatter
- No `# noqa: PLR0912/PLR0915` anywhere in `src/`

### Decomposition plan (per function)

1. `research_agent._execute_research_task`:
   - Extract `_recover_state()`, `_start_task()`, `_poll_task()`, `_finalize_task()`
2. `executor._run_live_checks`:
   - Extract each check into a small function: `_check_kill_switch()`, `_check_daily_budget()`, etc.
3. `cli/agent.py:research` and `cli/agent.py:analyze`:
   - Extract IO formatting vs orchestration; isolate “fetch inputs” vs “render output”
4. `cli/research.py:research_thesis_show`:
   - Split “fetch thesis” vs “fetch report” vs “render”
5. `cli/scan.py:scan_movers`:
   - Split “fetch markets” vs “compute movers” vs “render table”

## Definition of Done (Objective)

- [x] `rg -n \"noqa: PLR091\" src/kalshi_research` returns nothing
- [x] `uv run ruff check .` passes without needing those noqs
- [x] `uv run pytest` passes

## Acceptance Criteria (One-by-One)

- [x] Refactor `src/kalshi_research/agent/research_agent.py:_execute_research_task` (remove noqa, keep behavior)
- [x] Refactor `src/kalshi_research/execution/executor.py:_run_live_checks` (remove noqa, keep behavior)
- [x] Refactor `src/kalshi_research/cli/agent.py:research` (remove noqa, keep CLI UX)
- [x] Refactor `src/kalshi_research/cli/agent.py:analyze` (remove noqa, keep CLI UX)
- [x] Refactor `src/kalshi_research/cli/research.py:research_thesis_show` (remove noqa, keep CLI UX)
- [x] Refactor `src/kalshi_research/cli/scan.py:scan_movers` (remove noqa, keep CLI UX)

**Note (2026-01-20):** Implemented on `ralph-wiggum-loop`. All `# noqa: PLR0912/PLR0915` suppressions were removed from
`src/kalshi_research/`, with behavior preserved via unit tests.
