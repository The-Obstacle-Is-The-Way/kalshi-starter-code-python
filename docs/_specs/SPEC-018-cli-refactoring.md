# SPEC-018: CLI Refactoring

## Status
- **State**: Implemented
- **Created**: 2026-01-08
- **Completed**: 2026-01-08
- **Target Version**: 0.2.0

## Context
The current `src/kalshi_research/cli.py` file has grown to over 2,400 lines, violating the Single Responsibility Principle and making maintenance difficult. It contains logic for data collection, market analysis, alerts, research tracking, and portfolio management all in one file.

## Objectives
- Refactor `cli.py` into a modular package `src/kalshi_research/cli/`.
- Adhere to Clean Code principles and standard Typer multi-file application patterns.
- Ensure no regression in CLI functionality.
- Improve code navigability and testability.

## Proposed Structure

The monolithic `cli.py` will be replaced by a `cli/` package with the following structure:

```text
src/kalshi_research/cli/
├── __init__.py         # Main entry point, app definition, global callbacks
├── __main__.py         # Enables `python -m kalshi_research.cli` (daemon spawning)
├── utils.py            # Shared UI utilities (Rich console, JSON helpers)
├── data.py             # Data management commands
├── market.py           # Market lookup commands
├── scan.py             # Market scanning commands
├── alerts.py           # Alert management commands
├── analysis.py         # Analysis commands
├── research.py         # Research/Thesis commands
└── portfolio.py        # Portfolio commands
```

### Module Responsibilities

1.  **`__init__.py`**
    - Instantiates the main `typer.Typer` app (`kalshi`).
    - Defines the global `main` callback (environment setup, dotenv loading).
    - Registers sub-apps using `app.add_typer()`.
    - Implements the `version` command.
    - Exposes the `app` object for the entry point.

2.  **`__main__.py`**
    - **Critical**: Enables `python -m kalshi_research.cli` to work.
    - The daemon spawning logic (`_spawn_alert_monitor_daemon`) runs `python -m kalshi_research.cli alerts monitor`.
    - Without this file, daemon spawning will fail silently.
    - Contents: `from kalshi_research.cli import app; app()` (minimal).

3.  **`utils.py`**
    - Exports a shared `console = Console()` instance to ensure consistent output formatting.
    - Contains shared JSON file helpers used by alerts and research modules:
      - `_atomic_write_json(path, data)` — Atomic write with fsync.
      - `_load_json_storage_file(path, kind, required_list_key)` — Safe JSON loading with error handling.

4.  **`data.py`**
    - **Sub-app**: `data`
    - **Commands**: `init`, `sync-markets`, `sync-settlements`, `snapshot`, `collect`, `export`, `stats`.
    - **Imports**: `DatabaseManager`, `DataFetcher`, `DataScheduler`.

5.  **`market.py`**
    - **Sub-app**: `market`
    - **Commands**: `get`, `orderbook`, `list`.
    - **Imports**: `KalshiPublicClient`.

6.  **`scan.py`**
    - **Sub-app**: `scan`
    - **Commands**: `opportunities`, `arbitrage`, `movers`.
    - **Imports**: `MarketScanner`, `CorrelationAnalyzer`.

7.  **`alerts.py`**
    - **Sub-app**: `alerts`
    - **Commands**: `list`, `add`, `remove`, `monitor`.
    - **Internal Logic**:
      - `_spawn_alert_monitor_daemon()` — Spawns background monitor process.
      - `_get_alerts_file()` — Returns path to alerts JSON.

8.  **`analysis.py`**
    - **Sub-app**: `analysis`
    - **Commands**: `calibration`, `metrics`, `correlation`.
    - **Imports**: `CalibrationAnalyzer`, `CorrelationAnalyzer`.

9.  **`research.py`**
    - **Sub-app**: `research`
    - **Sub-app (nested)**: `thesis` (registered under `research` as `research.add_typer(thesis_app, name="thesis")`).
    - **Commands**: `thesis create`, `thesis list`, `thesis show`, `thesis resolve`, `backtest`.
    - **Internal Logic**: `_get_thesis_file()` — Returns path to theses JSON.

10. **`portfolio.py`**
    - **Sub-app**: `portfolio`
    - **Commands**: `sync`, `positions`, `pnl`, `balance`, `history`, `link`, `suggest-links`.
    - **Imports**: `PortfolioSyncer`, `KalshiClient`.

## Helper Functions Migration Map

The following internal functions must be relocated during refactoring:

| Function | Current Location | New Location | Notes |
|----------|------------------|--------------|-------|
| `_atomic_write_json()` | `cli.py:1024` | `cli/utils.py` | Shared by alerts + research |
| `_load_json_storage_file()` | `cli.py:1038` | `cli/utils.py` | Shared by alerts + research |
| `_get_alerts_file()` | `cli.py:1021` | `cli/alerts.py` | Module-specific |
| `_get_thesis_file()` | `cli.py:1540` | `cli/research.py` | Module-specific |
| `_spawn_alert_monitor_daemon()` | `cli.py:64` | `cli/alerts.py` | Module-specific |

## Implementation Plan

1.  **Create Directory Structure**:
    - Create `src/kalshi_research/cli/`.
    - Create empty `__init__.py`, `__main__.py`, and other module files.

2.  **Migrate Utils**:
    - Move `console` instantiation to `utils.py`.
    - Move `_atomic_write_json()` and `_load_json_storage_file()` to `utils.py`.

3.  **Migrate Sub-apps (Iterative)**:
    - For each sub-app (Data, Market, etc.):
        - Move the command functions to the respective module.
        - Create a local `typer.Typer()` instance in that module (e.g., `app = typer.Typer(help="...")`).
        - Update imports (fix relative imports, import `console` from `utils`).
        - Ensure local helper functions (like `_atomic_write_json`) are moved or shared.

4.  **Assemble Main App**:
    - In `src/kalshi_research/cli/__init__.py`:
        - Import the sub-apps: `from .data import app as data_app`.
        - Add them: `app.add_typer(data_app, name="data")`.
        - Implement the `main` callback.

5.  **Update Entry Point and Config**:
    - `pyproject.toml` entry point (`kalshi_research.cli:app`) remains valid — no change needed.
    - **Update `pyproject.toml` per-file-ignores** (line 99):
      ```toml
      # Before:
      "src/kalshi_research/cli.py" = ["PLC0415"]
      # After:
      "src/kalshi_research/cli/*.py" = ["PLC0415"]
      ```
    - Remove the original `src/kalshi_research/cli.py` file.

## Verification

1.  **Linting**: Run `uv run pre-commit run --all-files` to ensure imports are sorted and unused imports removed.
2.  **Manual Testing**: Run `uv run kalshi --help` to verify the command tree structure is preserved.
    - `uv run kalshi data --help`
    - `uv run kalshi research thesis list`
3.  **Automated Tests**: Run `uv run pytest`. The existing CLI tests (`tests/unit/test_cli.py`) import the app.
    - **Crucial**: The tests likely import `from kalshi_research.cli import app`. This import path must remain valid (i.e., `kalshi_research.cli` package must expose `app` in its `__init__.py`).

## Risk Mitigation
- **Import Errors**: Splitting files often breaks imports. We will rely on `ruff` and `mypy` to catch these.
- **Circular Imports**: Unlikely as the CLI modules are consumers of the core library, not dependencies of it.
- **Test Breakage**: The following test patches in `tests/unit/test_cli.py` must be updated:

  | Current Patch Target | New Patch Target |
  |---------------------|------------------|
  | `kalshi_research.cli._get_alerts_file` | `kalshi_research.cli.alerts._get_alerts_file` |
  | `kalshi_research.cli._get_thesis_file` | `kalshi_research.cli.research._get_thesis_file` |

- **Daemon Spawning**: The `_spawn_alert_monitor_daemon()` function runs `python -m kalshi_research.cli`. This requires `cli/__main__.py` to exist. Without it, daemon spawning fails silently.

## Refactoring Steps Checklist
- [x] Create `cli/` directory.
- [x] Create `cli/__main__.py` (critical for daemon spawning).
- [x] Create `cli/utils.py` with `console` and shared JSON helpers.
- [x] Refactor `Data` commands → `cli/data.py`.
- [x] Refactor `Market` commands → `cli/market.py`.
- [x] Refactor `Scan` commands → `cli/scan.py`.
- [x] Refactor `Alerts` commands → `cli/alerts.py`.
- [x] Refactor `Analysis` commands → `cli/analysis.py`.
- [x] Refactor `Research` commands → `cli/research.py`.
- [x] Refactor `Portfolio` commands (all 7) → `cli/portfolio.py`.
- [x] Create `cli/__init__.py` and wire everything up.
- [x] Update `pyproject.toml` per-file-ignores: `cli.py` → `cli/*.py`.
- [x] Update `tests/unit/test_cli.py` patch targets.
- [x] Delete `cli.py`.
- [x] Run verification suite (`pre-commit`, `pytest`, manual smoke tests).
