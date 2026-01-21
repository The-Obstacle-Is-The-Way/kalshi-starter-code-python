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
- [x] **DEBT-043-D7**: Split `agent/providers/llm.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [x] **DEBT-043-D8**: Split `execution/executor.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [x] **DEBT-043-D9**: Split `exa/client.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [x] **DEBT-043-D10**: Split `exa/websets/client.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [x] **DEBT-043-D11**: Split `portfolio/pnl.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [x] **DEBT-043-D12**: Split `portfolio/syncer.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [x] **DEBT-043-D13**: Split `analysis/liquidity.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [x] **DEBT-043-D14**: Split `analysis/scanner.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [x] **DEBT-043-D15**: Split `analysis/correlation.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [x] **DEBT-043-D16**: Split `api/models/portfolio.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [x] **DEBT-043-D17**: Split `research/thesis.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`
- [x] **DEBT-043-D18**: Split `data/fetcher.py` into focused modules → `docs/_debt/DEBT-043-srp-god-files.md`

### Phase 3: Final Verification

- [ ] **FINAL-GATES**: All quality gates pass (`pre-commit`, `mypy`, `pytest`, `mkdocs build --strict`)

---

## Work Log

- 2026-01-21: **DEBT-043-D18** complete — split `data/fetcher.py` (418 LoC) into 2 files: `_converters.py` (93), `fetcher.py` (344). Converter functions (`api_event_to_db`, `api_market_to_db`, `api_market_to_snapshot`, `api_market_to_settlement`) extracted to `_converters.py`. `DataFetcher` remains in `fetcher.py` delegating to module-level converter functions. Updated tests to use new module-level functions. All DEBT-043 Phase D complete (no files exceed 400 lines). Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D17** complete — split `research/thesis.py` (421 LoC) into 2 files: `_thesis_models.py` (253), `thesis.py` (177). Models (`ThesisStatus`, `ThesisEvidence`, `Thesis` dataclass) extracted to `_thesis_models.py`. `ThesisTracker` remains in `thesis.py` with re-exports preserving backwards-compatible public API. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D16** complete — split `api/models/portfolio.py` (428 LoC) into 6 files: `_balance.py` (20), `_position.py` (47), `_fill.py` (81), `_settlement.py` (66), `_order.py` (234), `portfolio.py` (55). Models grouped by domain (balance, position, fill, settlement, order). Re-exports preserve backwards-compatible public API. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D15** complete — split `analysis/correlation.py` (448 LoC) into 3 files: `_correlation_models.py` (98), `_arbitrage.py` (184), `correlation.py` (274). Models (`CorrelationType`, `CorrelationResult`, `ArbitrageOpportunity`) and `_is_priced` helper extracted to `_correlation_models.py`. Arbitrage functions (`find_inverse_markets`, `find_inverse_market_groups`, `find_arbitrage_opportunities`) extracted to `_arbitrage.py`. `CorrelationAnalyzer` delegates to module functions while preserving backwards-compatible class interface. Re-exports preserve public API. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D14** complete — split `analysis/scanner.py` (439 LoC) into 3 files: `_scanner_models.py` (46), `_verifier.py` (117), `scanner.py` (304). Models/types (`MarketClosedError`, `ScanFilter`, `ScanResult`) and `MarketStatusVerifier` extracted to separate modules. Re-exports preserve backwards-compatible public API. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D13** complete — split `analysis/liquidity.py` (461 LoC) into 5 files: `_liquidity_models.py` (87), `_depth.py` (67), `_slippage.py` (170), `_scoring.py` (149), `liquidity.py` (94). Re-exports preserve backwards-compatible public API. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D12** complete — split `portfolio/syncer.py` (483 LoC) into 6 files: `_sync_helpers.py` (81), `_sync_positions.py` (130), `_sync_trades.py` (116), `_sync_settlements.py` (99), `_mark_prices.py` (112), `syncer.py` (100). `PortfolioSyncer` delegates to module functions while preserving backwards-compatible class interface. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D11** complete — split `portfolio/pnl.py` (554 LoC) into 4 files: `_pnl_models.py` (80), `_fifo.py` (174), `_settlements.py` (191), `pnl.py` (276). `PnLCalculator` delegates to module functions while preserving backwards-compatible class interface. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D10** complete — split `exa/websets/client.py` (442 LoC) into mixins: `_http.py` (219), `_websets.py` (117), `_items.py` (80), `_searches.py` (100), `client.py` (54). Used mixin composition via multiple inheritance. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D9** complete — split `exa/client.py` (694 LoC) into mixins: `_http.py` (228), `_normalization.py` (50), `_search.py` (262), `_contents.py` (100), `_answer.py` (52), `_research.py` (178), `client.py` (54). Updated test patches to use new module paths. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D8** complete — split `execution/executor.py` (637 LoC) into `execution/` package with 4 new files: `_protocols.py` (49), `_checks.py` (307), `_orchestration.py` (189), `_executor.py` (340). Updated `__init__.py` to re-export from new modules. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D7** complete — split `agent/providers/llm.py` (471 LoC) into `agent/providers/llm/` package with 6 files: `__init__.py` (22), `_pricing.py` (69), `_prompts.py` (43), `_schemas.py` (74), `_claude.py` (244), `_mock.py` (68), `_factory.py` (40). Added TC001 exemption for Pydantic model. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D6** complete — split `agent/research_agent.py` (648 LoC) into `agent/research_agent/` package with 5 files: `__init__.py` (9), `_agent.py` (236), `_executor.py` (166), `_plan_builder.py` (152), `_recovery.py` (233). Updated test fixture to propagate state to executor/recovery. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D5** complete — reduced `cli/research/thesis/_commands.py` from 404 LoC to 355 LoC by moving `_check_thesis_invalidation` and `_gather_thesis_research_data` async helpers to `_helpers.py` (now 205 LoC). Updated `__init__.py` re-exports and test patches. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D4** complete — split `cli/alerts.py` (521 LoC) into `cli/alerts/` package with 7 files (largest: `monitor.py` at 218 LoC). Created `_helpers.py`, `list_cmd.py`, `add_cmd.py`, `remove.py`, `monitor.py`, `trim_log.py`, `__init__.py`. Updated tests to use new package paths. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D3** complete — split `cli/portfolio.py` (620 LoC) into `cli/portfolio/` package with 8 files (largest: `_helpers.py` at 129 LoC). Created `_helpers.py`, `sync.py`, `positions.py`, `pnl_cmd.py`, `balance.py`, `history.py`, `link.py`, `__init__.py`. Updated test to use new public `format_signed_currency` API. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D2** complete — split `cli/data.py` (737 LoC) into `cli/data/` package with 10 files (largest: `sync.py` at 225 LoC). Created `_helpers.py`, `init_cmd.py`, `migrate.py`, `sync.py`, `snapshot.py`, `collect.py`, `export_cmd.py`, `stats.py`, `maintenance.py`, `__init__.py`. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-043-D1** complete — split `cli/market.py` (788 LoC) into `cli/market/` package with 8 files (largest: `list.py` at 276 LoC). Created `_helpers.py`, `get.py`, `orderbook.py`, `liquidity.py`, `history.py`, `list.py`, `search.py`, `__init__.py`. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-047-C2** complete — added Exa cost-estimate constants (`EXA_SEARCH_TIER_SMALL_MAX`, `EXA_NEURAL_SEARCH_COST_*`, `EXA_DEEP_SEARCH_COST_*`, `EXA_PER_RESULT_*`, `EXA_ANSWER_*`, `EXA_COST_ESTIMATE_SAFETY_FACTOR`) to `constants.py`. Updated `exa/policy.py` to use them. DEBT-047 fully resolved. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: **DEBT-047-C1** complete — added `DEFAULT_AGENT_MAX_EXA_USD` and `DEFAULT_AGENT_MAX_LLM_USD` to `constants.py`, updated `agent/orchestrator.py` and `cli/agent.py` to use them. Quality gates: `pre-commit`, `pytest` (1052 passed).
- 2026-01-21: Reset queue post-branch-cleanup. Remaining active debt: DEBT-043 (Phase D) + DEBT-047 (Phase C).
