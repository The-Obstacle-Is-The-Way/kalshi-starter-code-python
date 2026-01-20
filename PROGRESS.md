# Kalshi Research Platform — Ralph Wiggum Progress Tracker

**Last Updated:** 2026-01-20
**Status:** Active (Debt Resolution Queue)
**Purpose:** State file for the Ralph Wiggum loop (see `docs/_ralph-wiggum/protocol.md`)

---

## Active Queue

### Phase 1: P1 Debt (Critical)

- [x] **DEBT-044-A**: Add `run_async()` helper to `cli/utils.py` → `docs/_debt/DEBT-044-dry-cli-boilerplate.md`
- [x] **DEBT-044-B**: Migrate all CLI modules off direct `asyncio.run()` → `docs/_debt/DEBT-044-dry-cli-boilerplate.md`
- [x] **DEBT-044-C**: Add `exit_kalshi_api_error()` helper → `docs/_debt/DEBT-044-dry-cli-boilerplate.md`
- [x] **DEBT-044-D**: Migrate all CLI modules off duplicated `except KalshiAPIError` → `docs/_debt/DEBT-044-dry-cli-boilerplate.md`
- [x] **DEBT-044-E**: Add DB session helper + migrate CLI DB plumbing → `docs/_debt/DEBT-044-dry-cli-boilerplate.md`

### Phase 2: P2 Debt (High)

- [x] **DEBT-045-A**: Refactor `agent/research_agent.py:_execute_research_task` (remove noqa) → `docs/_debt/DEBT-045-complexity-noqa-methods.md`
- [x] **DEBT-045-B**: Refactor `execution/executor.py:_run_live_checks` (remove noqa) → `docs/_debt/DEBT-045-complexity-noqa-methods.md`
- [x] **DEBT-045-C**: Refactor `cli/agent.py:research` (remove noqa) → `docs/_debt/DEBT-045-complexity-noqa-methods.md`
- [x] **DEBT-045-D**: Refactor `cli/agent.py:analyze` (remove noqa) → `docs/_debt/DEBT-045-complexity-noqa-methods.md`
- [x] **DEBT-045-E**: Refactor `cli/research.py:research_thesis_show` (remove noqa) → `docs/_debt/DEBT-045-complexity-noqa-methods.md`
- [x] **DEBT-045-F**: Refactor `cli/scan.py:scan_movers` (remove noqa) → `docs/_debt/DEBT-045-complexity-noqa-methods.md`

### Phase 3: P3 Debt (Medium)

- [x] **DEBT-046-B**: Migrate CLI modules to use `client_factory` (factory already exists) → `docs/_debt/DEBT-046-dependency-inversion-client-factory.md`
- [x] **DEBT-039-A**: Audit `executor.py` broad catches for safety → `docs/_debt/DEBT-039-broad-exception-catches.md`
- [x] **DEBT-039-B**: Add exception type logging to all broad catches → `docs/_debt/DEBT-039-broad-exception-catches.md`
- [x] **DEBT-047-A**: Introduce constants module + migrate pagination/depth defaults → `docs/_debt/DEBT-047-magic-numbers-policy-constants.md`
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
- 2026-01-20: Implemented DEBT-044-C: added `exit_kalshi_api_error()` helper to `cli/utils.py` (centralized error formatting + exit codes: 404→2, others→1). Migrated `cli/status.py` as template (3 call sites). Added 6 unit tests. Quality gates pass (pre-commit, mypy, pytest 1009 tests).
- 2026-01-20: Implemented DEBT-044-D: migrated all CLI modules (12 files, 25 call sites) to use `exit_kalshi_api_error()` helper. 3 special cases intentionally preserved (news.py ValueError re-raise, scan.py and event.py warning+continue patterns). Quality gates pass (pre-commit, mypy, pytest 1009 tests).
- 2026-01-20: Implemented DEBT-044-E: migrated all CLI modules (6 files, 11 call sites) off direct `DatabaseManager()` to use `open_db()`/`open_db_session()` helpers from `cli/db.py`. Helpers already existed; migration was mechanical. Now only `cli/db.py` contains `DatabaseManager`. Quality gates pass (pre-commit, mypy, pytest 1009 tests). DEBT-044 complete.
- 2026-01-20: Implemented DEBT-045-A: refactored `_execute_research_task` (147 lines → 32 lines main + 6 helper methods). Extracted `_recover_or_create_research_task()`, `_try_recover_from_saved_state()`, `_try_recover_by_id()`, `_try_recover_by_list()`, `_create_new_research_task()`, `_is_terminal_status()`, `_wait_for_research_task()`, `_finalize_research_task()`. Removed noqa comment. All 27 research_agent tests pass. Quality gates pass (pre-commit, mypy, pytest 1009 tests).
- 2026-01-20: Implemented DEBT-045-B: refactored `_run_live_checks` (121 lines → 32 lines main + 8 helper methods). Extracted `_check_kill_switch()`, `_check_production_gating()`, `_check_daily_order_limit()`, `_check_budget_limits()`, `_check_position_cap()`, `_check_orderbook_safety()`, `_check_liquidity_grade()`, `_check_confirmation()`. Removed noqa comment. All 18 executor tests pass. Quality gates pass (pre-commit, mypy, pytest 1009 tests).
- 2026-01-20: Implemented DEBT-045-C: refactored `cli/agent.py:research` (157 lines → 28 lines main + 5 helper functions). Extracted `_parse_exa_mode()`, `_write_json_output()`, `_render_research_summary()`, `_render_factors_table()`, `_execute_research()`. Removed noqa comment. Updated integration tests to expect exit code 2 for 404 errors (per CLI convention). Quality gates pass (pre-commit, mypy, pytest).
- 2026-01-20: Implemented DEBT-045-D: refactored `cli/agent.py:analyze` (192 lines → 60 lines main + 4 helper functions). Extracted `_execute_analysis()`, `_render_analysis_human()`, `_render_analysis_factors_table()`, `_output_analysis_json()`. Removed noqa comment. Quality gates pass (pre-commit, mypy, pytest 1009 tests).
- 2026-01-20: Implemented DEBT-045-E: refactored `cli/research.py:research_thesis_show` (124 lines → 24 lines main + 6 helper functions). Extracted `_find_thesis_by_id()`, `_render_thesis_header()`, `_render_thesis_fields_table()`, `_render_thesis_cases_and_updates()`, `_render_thesis_evidence()`, `_fetch_and_render_linked_positions()`. Removed noqa comment. Quality gates pass (pre-commit, mypy, pytest 1009 tests).
- 2026-01-20: Implemented DEBT-045-F: refactored `cli/scan.py:scan_movers` (149 lines → 47 lines main + 4 helper functions). Extracted `_parse_movers_period()`, `_fetch_movers_market_lookup()`, `_compute_movers()`, `_render_movers_table()`. Removed noqa comment. DEBT-045 now complete (all noqa: PLR091 removed from src/). Quality gates pass (pre-commit, mypy, pytest 1009 tests).
- 2026-01-20: Implemented DEBT-046-B: migrated CLI modules to `client_factory.public_client()` / `authed_client()`, updated CLI unit/integration tests to patch factory functions. Fixed order-dependent CLI tests caused by constructor patch leakage. Quality gates pass (pre-commit, mypy, pytest).
- 2026-01-20: Implemented DEBT-039-A: audited `executor.py` broad exception catches for safety. Narrowed `_check_orderbook_safety` and `_check_liquidity_grade` to `(KalshiAPIError, httpx.HTTPError, httpx.TimeoutException)` with exception type logging. Documented `create_order` audit catch as intentionally broad (re-raises, audit-only). Added 5 new tests for narrowed exception handling. Quality gates pass (pre-commit, mypy, pytest 1014 tests).
- 2026-01-20: Implemented DEBT-039-B: added `exc_info=True` to broad exception catches (`research/invalidation.py:128`, `research/thesis_research.py:313`, `api/websocket/client.py:275`, `exa/cache.py:141`). Narrowed cache exception catches from `Exception` to `(json.JSONDecodeError, KeyError, ValueError, TypeError, OSError)`. DEBT-039 now complete. Quality gates pass (pre-commit, mypy, pytest).
- 2026-01-20: Implemented DEBT-047-A: created `src/kalshi_research/constants.py` with `DEFAULT_PAGINATION_LIMIT=200` and `DEFAULT_ORDERBOOK_DEPTH=10`. Migrated 4 files (data/fetcher.py, cli/scan.py, cli/market.py, api/client.py) to use constants. Grep checks confirm no `limit=200` or `depth: int = 10` literals remain. Quality gates pass (pre-commit, mypy, pytest 1014 tests).

---

## Completion Criteria

The queue is complete when there are no unchecked items (no lines matching the unchecked-task pattern at column 0).
The loop operator should verify completion via this file's state, not by parsing model output.
