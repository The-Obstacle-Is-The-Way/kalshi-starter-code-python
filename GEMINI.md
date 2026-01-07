# Kalshi Research Platform

The **Kalshi Research Platform** is a Python-based toolset designed for analyzing prediction markets on Kalshi. It focuses on research, data collection, and thesis tracking rather than automated high-frequency trading.

## Project Overview

This platform enables users to:
*   **Collect and Store Data:** Sync markets, events, and price snapshots to a local SQLite database (with async support).
*   **Analyze Markets:** Perform calibration analysis, detect edges, scan for arbitrage, and identify significant price movers.
*   **Track Theses:** Create and track research theses, link them to positions, and resolve them to measure accuracy.
*   **Monitor Portfolios:** View current positions, calculate P&L, and analyze trade history.
*   **Alerting:** Set up alerts for price, volume, and spread conditions.

### Key Technologies
*   **Language:** Python 3.11+
*   **Package Manager:** `uv`
*   **CLI Framework:** `typer`
*   **Database:** `sqlalchemy` (async) + `aiosqlite`
*   **Data Analysis:** `pandas`, `numpy`, `scipy`, `duckdb`
*   **HTTP Client:** `httpx`
*   **Validation:** `pydantic`

## Building and Running

### Prerequisites
*   Python 3.11 or higher
*   `uv` (Universal Python Package Manager)

### Setup
1.  **Install Dependencies:**
    ```bash
    uv sync
    ```
2.  **Initialize Database:**
    ```bash
    uv run kalshi data init
    ```

### CLI Usage
The application is accessed via the `kalshi` command (run via `uv run`).

*   **Main Help:**
    ```bash
    uv run kalshi --help
    ```

*   **Data Collection:**
    ```bash
    # Sync market definitions
    uv run kalshi data sync-markets

    # Continuous collection (runs in loop)
    uv run kalshi data collect --interval 15
    ```

*   **Market Scanning:**
    ```bash
    # Scan for opportunities (e.g., close races)
    uv run kalshi scan opportunities --filter close-race

    # Find arbitrage opportunities
    uv run kalshi scan arbitrage
    ```

*   **Research & Theses:**
    ```bash
    # Create a new thesis
    uv run kalshi research thesis create "Bitcoin > 100k" --markets KXBTC --your-prob 0.65 --market-prob 0.45

    # List theses
    uv run kalshi research thesis list
    ```

*   **Analysis:**
    ```bash
    # Analyze calibration (Brier scores)
    uv run kalshi analysis calibration --days 30
    ```

## Development Conventions

### Coding Standards
*   **Strict Typing:** The project enforces strict type checking using `mypy`. All functions must have type hints.
*   **Linting & Formatting:** `ruff` is used for both linting and formatting.
*   **AsyncIO:** The codebase is primarily async. Database interactions and API calls should be awaited.

### Testing
*   **Framework:** `pytest`
*   **Running Tests:**
    ```bash
    uv run pytest
    ```
*   **Coverage:**
    ```bash
    uv run pytest --cov=kalshi_research
    ```

### Quality Gates
Before committing, ensure all quality checks pass:
```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest tests/unit
```

### Directory Structure
*   `src/kalshi_research/`: Main source code.
    *   `api/`: Kalshi API client and models.
    *   `data/`: Database models, repositories, and fetchers.
    *   `analysis/`: Logic for calibration, scanning, and edge detection.
    *   `research/`: Thesis management.
    *   `portfolio/`: Position and P&L tracking.
    *   `alerts/`: Alert monitoring system.
    *   `cli.py`: Typer CLI application entry point.
*   `tests/`: Unit and integration tests.
*   `docs/`: Documentation and specifications (`_specs`).
*   `notebooks/`: Jupyter notebooks for exploratory analysis.
