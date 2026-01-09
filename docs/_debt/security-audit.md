# Security Audit Report

**Date**: 2026-01-09
**Scope**: `src/kalshi_research`
**Focus**: Agent Safety, Credential Handling, Injection Risks

## Executive Summary
The codebase is generally secure for a research tool, but lacks specific safeguards required for **Autonomous Agent** usage. The primary risk is financial (unintended trading), not system compromise.

## Critical Risks (Action Required)

### 1. Agent Harness Safety (Financial Risk)
*   **Issue**: `KalshiClient.create_order` executes immediately. An LLM agent using this tool has no "undo" button and no safety net.
*   **Mitigation**: Created **TODO-008 (Agent Safety Rails)** to implement `dry_run` and a `TradeExecutor` with budget limits.

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
1.  **Implement TODO-008 immediately** if agents are to be enabled.
2.  ~~Add input validation to `src/kalshi_research/data/export.py` for file paths.~~ ✅ Already implemented.
3.  Add a `SECURITY.md` to the root if open-sourcing.
