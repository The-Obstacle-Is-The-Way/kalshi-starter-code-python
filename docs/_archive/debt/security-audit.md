# Security Audit Report

**Date**: 2026-01-09
**Scope**: `src/kalshi_research`
**Focus**: Agent Safety, Credential Handling, Injection Risks

## Executive Summary
The codebase is generally secure for a research tool, but lacks specific safeguards required for **Autonomous Agent** usage. The primary risk is financial (unintended trading), not system compromise.

## Critical Risks (Action Required)

### 1. Agent Harness Safety (Financial Risk)
*   **Issue**: Kalshi write endpoints are accessible via `KalshiClient` methods. Any automation (LLM/agent/cron) must not call these directly without a safety boundary.
*   **Mitigation (2026-01-10)**: Implemented `TradeExecutor` as the safety boundary:
    *   `src/kalshi_research/execution/executor.py` (safe-by-default: `live=False` ⇒ `dry_run=True`)
    *   kill switch (`KALSHI_TRADE_KILL_SWITCH=1`), environment gating, confirmation gate for live, per-order risk cap, per-day order cap
    *   append-only JSONL audit log (`data/trade_audit.log` by default)
*   **Remaining (Phase 2, if autonomous trading is enabled)**: daily budgets / position caps / liquidity-aware sizing (see `docs/_specs/SPEC-034-trade-executor-safety-harness.md`).

### 2. DuckDB Export Injection (Local Risk) - CLEARED
*   **Location**: `src/kalshi_research/data/export.py:43-46`
*   **Issue**: `conn.execute(f"ATTACH '{sqlite_path}' ...")` uses f-string formatting with a file path.
*   **Verdict**: **Safe**. Path validation exists at lines 43-46:
    ```python
    if any(c in str(path) for c in ["'", '"', ";", "--"]):
        raise ValueError(f"Invalid characters in path: {path}")
    ```
*   **Note**: The code also validates table names against `ALLOWED_TABLES` allowlist (line 64).

## Cleared Items (Verified Safe)

### 1. Shell Injection
*   **Finding**: Usage of `subprocess` in `cli/alerts.py` uses `DETACHED_PROCESS` and explicit argument lists (no `shell=True`).
*   **Verdict**: **Safe**. Standard daemonization pattern.

### 2. Credential Logging
*   **Finding**: `KalshiClient` and `KalshiAuth` use `structlog`.
*   **Verification**: No instances of logging full headers, API keys, or private keys found in `INFO` or `DEBUG` logs.
*   **Verdict**: **Safe**.

### 3. SQL Injection (Core Data)
*   **Finding**: `src/kalshi_research/data/repositories` uses SQLAlchemy ORM (`stmt = select(...)`).
*   **Verdict**: **Safe**.

### 4. Hardcoded Secrets
*   **Finding**: Configuration uses `dotenv` and `os.getenv`. No committed keys found in source.
*   **Verdict**: **Safe**.

## Recommendations
1.  **Use `TradeExecutor` for all trading attempts** (and keep agent loops from importing/using `KalshiClient` trading methods directly).
2.  If/when autonomous trading is enabled, complete Phase 2 safety rails in `docs/_specs/SPEC-034-trade-executor-safety-harness.md`.
2.  ~~Add input validation to `src/kalshi_research/data/export.py` for file paths.~~ ✅ Already implemented.
3.  Add a `SECURITY.md` to the root if open-sourcing.
