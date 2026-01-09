# Kalshi Research Platform - Progress Tracker

**Last Updated:** 2026-01-09
**Purpose:** State file for Ralph Wiggum loop - fixes bugs, debt, and TODOs

---

## Phase 1: Critical Bug Fixes

- [x] **BUG-048**: Fix negative liquidity validation (REOPENED - see updated doc) → `api/models/market.py`
- [x] **BUG-050**: Add logging to silent exception → `cli/alerts.py:117`

## Phase 2: Safety-Critical Fixes

- [x] **BUG-049**: Add rate limiter to read operations → `api/client.py`
- [x] **TODO-007**: Implement `MarketStatusVerifier` → `analysis/scanner.py`
- [x] **TODO-008**: Add `dry_run` parameter to `create_order` → `api/client.py`

## Phase 2.5: URGENT - API Deprecation (Deadline: Jan 15, 2026)

- [x] **TODO-009**: Migrate from cent fields to dollar fields → `api/models/market.py` ⚠️ **6 DAYS**

## Phase 3: Research Quality

- [x] **TODO-005**: Add `open_time`/`created_time` to `market get` → `cli/market.py`
- [x] **BUG-047**: Investigate portfolio sync discrepancy → `portfolio/syncer.py`

## Phase 4: Technical Debt

- [ ] **DEBT-002**: Complete Phase 1 magic number comments → `api/client.py`
- [ ] **DEBT-003**: Add `session.begin()` transaction boundaries → `data/repositories/`
- [ ] **DEBT-001**: Create Pydantic models for portfolio methods → `api/models/portfolio.py`

## Phase 5: Session Friction (TODO-006)

- [ ] **TODO-006**: Implement remaining code fixes from friction audit

## Phase 6: Verification

- [ ] **FINAL-001**: All quality gates pass (ruff, mypy, pytest)
- [ ] **FINAL-002**: Pre-commit hooks run successfully

---

## Completion Criteria

When ALL boxes are checked AND all quality gates pass, the cleanup is complete.
The loop operator verifies completion by checking this file's state (all `[x]`).
