# Kalshi Research Platform — Ralph Wiggum Progress Tracker

**Last Updated:** 2026-01-21
**Status:** Active (kalshi-ralph sandbox)
**Purpose:** State file for the Ralph Wiggum loop (see `docs/_ralph-wiggum/protocol.md`)

---

## Active Queue

### Phase 1: P3 Debt (Small, mechanical)

- [x] **DEBT-047-C1**: Centralize agent default budgets (`max_exa_usd` / `max_llm_usd`) → `docs/_debt/DEBT-047-magic-numbers-policy-constants.md`
- [x] **DEBT-047-C2**: Centralize Exa cost-estimate literals (tiers/per-page/safety factors) → `docs/_debt/DEBT-047-magic-numbers-policy-constants.md`

### Phase 2: P1 Debt (Large, refactors to ≤400 LoC)

- [x] **DEBT-043-D1**: Split `cli/market.py` → `cli/market/` package → `docs/_debt/DEBT-043-srp-god-files.md`
- [x] **DEBT-043-D2**: Split `cli/data.py` → `cli/data/` package → `docs/_debt/DEBT-043-srp-god-files.md`
- [x] **DEBT-043-D3**: Split `cli/portfolio.py` → `cli/portfolio/` package → `docs/_debt/DEBT-043-srp-god-files.md`
- [x] **DEBT-043-D4**: Split `cli/alerts.py` → `cli/alerts/` package → `docs/_debt/DEBT-043-srp-god-files.md`
- [x] **DEBT-043-D5**: Reduce `cli/research/thesis/_commands.py` to ≤400 LoC → `docs/_debt/DEBT-043-srp-god-files.md`
- [x] **DEBT-043-D6**: Split `agent/research_agent.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [ ] **DEBT-043-D7**: Split `agent/providers/llm.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [ ] **DEBT-043-D8**: Split `execution/executor.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [ ] **DEBT-043-D9**: Split `exa/client.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [ ] **DEBT-043-D10**: Split `exa/websets/client.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [ ] **DEBT-043-D11**: Split `portfolio/pnl.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [ ] **DEBT-043-D12**: Split `portfolio/syncer.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [ ] **DEBT-043-D13**: Split `analysis/liquidity.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [ ] **DEBT-043-D14**: Split `analysis/scanner.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [ ] **DEBT-043-D15**: Split `analysis/correlation.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [ ] **DEBT-043-D16**: Split `api/models/portfolio.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [ ] **DEBT-043-D17**: Split `research/thesis.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [ ] **DEBT-043-D18**: Split `data/fetcher.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`

### Phase 3: Final Verification

- [ ] **FINAL-GATES**: All quality gates pass (`pre-commit`, `mypy`, `pytest`, `mkdocs build --strict`)

---

## Work Log

- 2026-01-21: **DEBT-043-D6** complete — split `agent/research_agent.py` (648 LoC) into `agent/research_agent/` package with 5 files: `__init__.py` (9), `_agent.py` (236), `_executor.py` (166), `_plan_builder.py` (152), `_recovery.py` (233). Updated test fixture to propagate state to executor/recovery. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D5** complete — reduced `cli/research/thesis/_commands.py` from 404 LoC to 355 LoC by moving `_check_thesis_invalidation` and `_gather_thesis_research_data` async helpers to `_helpers.py` (now 205 LoC). Updated `__init__.py` re-exports and test patches. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D4** complete — split `cli/alerts.py` (521 LoC) into `cli/alerts/` package with 7 files (largest: `monitor.py` at 218 LoC). Created `_helpers.py`, `list_cmd.py`, `add_cmd.py`, `remove.py`, `monitor.py`, `trim_log.py`, `__init__.py`. Updated tests to use new package paths. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D3** complete — split `cli/portfolio.py` (620 LoC) into `cli/portfolio/` package with 8 files (largest: `_helpers.py` at 129 LoC). Created `_helpers.py`, `sync.py`, `positions.py`, `pnl_cmd.py`, `balance.py`, `history.py`, `link.py`, `__init__.py`. Updated test to use new public `format_signed_currency` API. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D2** complete — split `cli/data.py` (737 LoC) into `cli/data/` package with 10 files (largest: `sync.py` at 225 LoC). Created `_helpers.py`, `init_cmd.py`, `migrate.py`, `sync.py`, `snapshot.py`, `collect.py`, `export_cmd.py`, `stats.py`, `maintenance.py`, `__init__.py`. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D1** complete — split `cli/market.py` (788 LoC) into `cli/market/` package with 8 files (largest: `list.py` at 276 LoC). Created `_helpers.py`, `get.py`, `orderbook.py`, `liquidity.py`, `history.py`, `list.py`, `search.py`, `__init__.py`. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-047-C2** complete — added Exa cost-estimate constants (`EXA_SEARCH_TIER_SMALL_MAX`, `EXA_NEURAL_SEARCH_COST_*`, `EXA_DEEP_SEARCH_COST_*`, `EXA_PER_RESULT_*`, `EXA_ANSWER_*`, `EXA_COST_ESTIMATE_SAFETY_FACTOR`) to `constants.py`. Updated `exa/policy.py` to use them. DEBT-047 fully resolved. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-047-C1** complete — added `DEFAULT_AGENT_MAX_EXA_USD` and `DEFAULT_AGENT_MAX_LLM_USD` to `constants.py`, updated `agent/orchestrator.py` and `cli/agent.py` to use them. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: Reset queue post-branch-cleanup. Remaining active debt: DEBT-043 (Phase D) + DEBT-047 (Phase C).
