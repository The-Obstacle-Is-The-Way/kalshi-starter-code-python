# Kalshi Research Platform — Ralph Wiggum Progress Tracker

**Last Updated:** 2026-01-20
**Status:** Active (Debt Resolution Queue)
**Purpose:** State file for the Ralph Wiggum loop (see `docs/_ralph-wiggum/protocol.md`)

---

## Active Queue

### Phase 1: P1 Debt (Critical)

- [x] **DEBT-044-A**: Add `run_async()` helper to `cli/utils.py` → `docs/_debt/DEBT-044-dry-cli-boilerplate.md`
- [x] **DEBT-044-B**: Migrate all CLI modules off direct `asyncio.run()` → `docs/_debt/DEBT-044-dry-cli-boilerplate.md`
- [ ] **DEBT-044-C**: Add `exit_kalshi_api_error()` helper → `docs/_debt/DEBT-044-dry-cli-boilerplate.md`
- [ ] **DEBT-044-D**: Migrate all CLI modules off duplicated `except KalshiAPIError` → `docs/_debt/DEBT-044-dry-cli-boilerplate.md`
- [ ] **DEBT-044-E**: Add DB session helper + migrate CLI DB plumbing → `docs/_debt/DEBT-044-dry-cli-boilerplate.md`

### Phase 2: P2 Debt (High)

- [ ] **DEBT-045-A**: Refactor `agent/research_agent.py:_execute_research_task` (remove noqa) → `docs/_debt/DEBT-045-complexity-noqa-methods.md`
- [ ] **DEBT-045-B**: Refactor `execution/executor.py:_run_live_checks` (remove noqa) → `docs/_debt/DEBT-045-complexity-noqa-methods.md`
- [ ] **DEBT-045-C**: Refactor `cli/agent.py:research` (remove noqa) → `docs/_debt/DEBT-045-complexity-noqa-methods.md`
- [ ] **DEBT-045-D**: Refactor `cli/agent.py:analyze` (remove noqa) → `docs/_debt/DEBT-045-complexity-noqa-methods.md`
- [ ] **DEBT-045-E**: Refactor `cli/research.py:research_thesis_show` (remove noqa) → `docs/_debt/DEBT-045-complexity-noqa-methods.md`
- [ ] **DEBT-045-F**: Refactor `cli/scan.py:scan_movers` (remove noqa) → `docs/_debt/DEBT-045-complexity-noqa-methods.md`

### Phase 3: P3 Debt (Medium)

- [ ] **DEBT-046-B**: Migrate CLI modules to use `client_factory` (factory already exists) → `docs/_debt/DEBT-046-dependency-inversion-client-factory.md`
- [ ] **DEBT-039-A**: Audit `executor.py` broad catches for safety → `docs/_debt/DEBT-039-broad-exception-catches.md`
- [ ] **DEBT-039-B**: Add exception type logging to all broad catches → `docs/_debt/DEBT-039-broad-exception-catches.md`
- [ ] **DEBT-047-A**: Introduce constants module + migrate pagination/depth defaults → `docs/_debt/DEBT-047-magic-numbers-policy-constants.md`
- [ ] **DEBT-047-B**: Migrate scanner/liquidity threshold literals → `docs/_debt/DEBT-047-magic-numbers-policy-constants.md`

### Phase 4: P1 Debt (Large - After Phases 1-3)

- [ ] **DEBT-043-A**: Split `cli/research.py` into `cli/research/` package → `docs/_debt/DEBT-043-srp-god-files.md`
- [ ] **DEBT-043-B**: Split `cli/scan.py` into `cli/scan/` package → `docs/_debt/DEBT-043-srp-god-files.md`
- [ ] **DEBT-043-C**: Split `api/client.py` into endpoint modules → `docs/_debt/DEBT-043-srp-god-files.md`

### Phase 5: Final Verification

- [ ] **FINAL-GATES**: All quality gates pass (`pre-commit`, `mypy`, `pytest`, `mkdocs build --strict`)

---

**Guidelines:**

- Read [`AGENTS.md`](AGENTS.md) first (project intent + safety constraints).
- One task per iteration; if a DEBT item is too large for a single safe change, it's already split (e.g., `DEBT-044-A`, `DEBT-044-B`).
- Avoid cost-incurring or irreversible operations during the loop (paid Exa calls, live trading, live LLM). Prefer unit tests + fixtures.
- Preserve public API/CLI surfaces; refactors should be mechanical, test-backed, and easy to review/revert.
- Update the corresponding DEBT-XXX.md acceptance criteria as you complete each sub-task.

---

## Work Log

- 2026-01-19: Reset PROGRESS.md for debt resolution queue (DEBT-039, 043, 044, 045, 046, 047). Debt docs verified against SSOT. client_factory.py salvaged from prior branch. Starting fresh on all migrations.
- 2026-01-20: Implemented DEBT-044-A: added `kalshi_research.cli.utils.run_async()` (centralized `asyncio.run` + Ctrl+C exit 130), migrated `cli/status.py` as the template (3 call sites), added unit tests. Quality gates pass (`uv run pre-commit run --all-files`, `uv run pytest`).
- 2026-01-20: Documentation cleanup: removed Gemini references (no longer used), added ANTHROPIC_API_KEY billing docs to Ralph Wiggum protocol (shell export = API credits, .env only = subscription).
- 2026-01-20: Implemented DEBT-044-B: migrated all CLI modules (13 files, 55 call sites) from direct `asyncio.run()` to centralized `run_async()` helper. Only `utils.py:run_async()` now contains `asyncio.run`. Quality gates pass (pre-commit, mypy, pytest 1003 tests).

---

## Completion Criteria

The queue is complete when there are no unchecked items (no lines matching the unchecked-task pattern at column 0).
The loop operator should verify completion via this file's state, not by parsing model output.
