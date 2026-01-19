# Kalshi Research Platform

This file provides guidance to Gemini CLI and Gemini Code Assist when working with this repository.

## Project Intent (Avoid Over-Engineering)

This repository is an **internal, single-user research CLI** (plus local SQLite cache) for a solo trader.
It is **not** a multi-user production service.

- Prefer **simple, testable** changes over “enterprise patterns”.
- Do **not** add service infrastructure (circuit breakers, Prometheus/Otel, request tracing, DI) unless a SPEC/BUG
  explicitly requires it.
- Keep dependencies minimal; focus on correctness, clear UX, and robust error handling.

## Agent Skills

This repository includes Agent Skills for enhanced CLI navigation and documentation auditing:

| Skill | Location | Purpose |
|-------|----------|---------|
| `kalshi-cli` | `.gemini/skills/kalshi-cli/` | CLI commands, database queries, workflows, gotchas |
| `kalshi-codebase` | `.gemini/skills/kalshi-codebase/` | Repo navigation and codebase structure |
| `kalshi-ralph-wiggum` | `.gemini/skills/kalshi-ralph-wiggum/` | Ralph Wiggum autonomous loop operation |
| `kalshi-doc-audit` | `.gemini/skills/kalshi-doc-audit/` | Documentation auditing against SSOT |

Skills are also mirrored to `.claude/skills/` and `.codex/skills/` for other agents.

## CRITICAL: Commit Safety Protocol

**NEVER commit code without running quality gates first.** A previous incident introduced syntax corruption (`时不时` instead of `import`) that broke the entire codebase. This was caused by committing without pre-commit hooks installed.

### MANDATORY Before ANY Commit

```bash
# 1. FIRST: Ensure pre-commit hooks are installed (do this ONCE after clone)
uv run pre-commit install

# 2. ALWAYS run pre-commit before staging/committing
uv run pre-commit run --all-files

# 3. If pre-commit passes, THEN commit
git add . && git commit -m "Your message"

# 4. NEVER use --no-verify to bypass hooks
# git commit --no-verify  # <- FORBIDDEN
```

### Pre-commit Will Automatically Check

1. **Python syntax validation** (`check-ast`) - Catches encoding corruption
2. **Ruff linting** - Code quality and style
3. **Ruff formatting** - Consistent formatting
4. **Mypy type checking** - Static type safety
5. **Unit tests** - Quick smoke test

### FORBIDDEN Patterns

- **NO `# type: ignore`** - Fix the type error properly
- **NO untyped `Any`** - Use specific types (exception: JSON dicts as `dict[str, Any]`)
- **NO `--no-verify` commits** - Always run pre-commit hooks
- **NO manual git commits without pre-commit** - Always verify first

## Project Overview

This platform enables users to:
* **Collect and Store Data:** Sync markets, events, and price snapshots to a local SQLite database (with async support).
* **Analyze Markets:** Perform calibration analysis, detect edges, scan for arbitrage, and identify significant price movers.
* **Track Theses:** Create and track research theses, link them to positions, and resolve them to measure accuracy.
* **Monitor Portfolios:** View current positions, calculate P&L, and analyze trade history.
* **Alerting:** Set up alerts for price, volume, spread, and sentiment shift conditions.
* **News & Research:** Collect news via Exa API, run sentiment analysis, research topics, and manage async deep research tasks (with crash recovery).

### Key Technologies
* **Language:** Python 3.11+
* **Package Manager:** `uv`
* **CLI Framework:** `typer`
* **Database:** `sqlalchemy` (async) + `aiosqlite`
* **Data Analysis:** `pandas`, `numpy`, `scipy`, `duckdb`
* **HTTP Client:** `httpx`
* **Validation:** `pydantic`

## Building and Running

### Prerequisites
* Python 3.11 or higher
* `uv` (Universal Python Package Manager)

### Setup
1. **Install Dependencies:**
   ```bash
   uv sync --all-extras
   ```
2. **Install Pre-commit Hooks (CRITICAL):**
   ```bash
   uv run pre-commit install
   ```
3. **Initialize Database:**
   ```bash
   uv run kalshi data init
   ```

### CLI Usage
The application is accessed via the `kalshi` command (run via `uv run`).

* **Main Help:**
  ```bash
  uv run kalshi --help
  ```

* **Data Collection:**
  ```bash
  # Sync market definitions
  uv run kalshi data sync-markets

  # Continuous collection (runs in loop)
  uv run kalshi data collect --interval 15
  ```

* **Market Scanning:**
  ```bash
  # Scan for opportunities (e.g., close races)
  uv run kalshi scan opportunities --filter close-race

  # Find arbitrage opportunities
  uv run kalshi scan arbitrage
  ```

* **Research & Theses:**
  ```bash
  # Create a new thesis
  uv run kalshi research thesis create "Bitcoin > 100k" \
    --markets KXBTC \
    --your-prob 0.65 \
    --market-prob 0.45 \
    --confidence 0.8

  # List theses
  uv run kalshi research thesis list

  # Exa-powered research (requires EXA_API_KEY)
  EXA_API_KEY=... uv run kalshi research topic "Will the Fed cut rates in 2026?"
  EXA_API_KEY=... uv run kalshi research deep "Summarize what could cause this market to resolve YES." --model exa-research-fast --wait
  ```

* **News Monitoring:**
  ```bash
  # Track a market for news
  uv run kalshi news track TICKER

  # Collect news and sentiment
  EXA_API_KEY=... uv run kalshi news collect
  ```

* **Analysis:**
  ```bash
  # Analyze calibration (Brier scores)
  uv run kalshi analysis calibration --days 30
  ```

## Development Conventions

### Coding Standards
* **Strict Typing:** The project enforces strict type checking using `mypy`. All functions must have type hints.
* **Linting & Formatting:** `ruff` is used for both linting and formatting.
* **AsyncIO:** The codebase is primarily async. Database interactions and API calls should be awaited.

### Testing
* **Framework:** `pytest`
* **Running Tests:**
  ```bash
  uv run pytest
  ```
* **Coverage:**
  ```bash
  uv run pytest --cov=kalshi_research
  ```

### Quality Gates
Before committing, **ALWAYS** run pre-commit:
```bash
uv run pre-commit run --all-files
```

This will automatically check:
- Python syntax (AST validation)
- Ruff linting and formatting
- Mypy type checking
- Unit tests

### Database Safety (Do Not Destroy State)

- **NEVER delete `data/kalshi.db`** to "fix" corruption. Diagnose and recover instead:
  - `sqlite3 data/kalshi.db "PRAGMA integrity_check;"`
  - `sqlite3 data/kalshi.db ".recover" | sqlite3 data/recovered.db`
- `data/exa_cache/` is safe to delete; the SQLite DB is not.
- **SQLite concurrency:** Avoid running two write-heavy commands simultaneously (e.g., two `data sync-markets` in parallel). SQLite locks the entire DB on write; concurrent writers will get "database is locked" errors.
- See `.gemini/skills/kalshi-cli/GOTCHAS.md` for the full "Critical Anti-Patterns" section.

### Directory Structure
* `src/kalshi_research/`: Main source code.
  * `api/`: Kalshi API client and models.
  * `data/`: Database models, repositories, and fetchers.
  * `exa/`: Exa API client for research.
  * `news/`: News collection and sentiment analysis.
  * `analysis/`: Logic for calibration, scanning, and edge detection.
  * `research/`: Thesis management.
  * `portfolio/`: Position and P&L tracking.
  * `alerts/`: Alert monitoring system.
  * `cli/`: Typer CLI application package entry point.
* `tests/`: Unit and integration tests.
* `docs/`: Documentation and specifications (`_specs`).
* `notebooks/`: Jupyter notebooks for exploratory analysis.

## Runtime Environment & API Access

**Agents CAN and SHOULD read `.env`** to understand the configured environment. While `.env` is gitignored (never commit it), reading it is necessary to:

- Determine if `KALSHI_ENVIRONMENT` is set to `prod` or `demo`
- Verify API credentials are configured before running authenticated commands
- Avoid confusion about which environment is active

### Environment Behavior

| `KALSHI_ENVIRONMENT` | API Base URL                 | Real Money? |
|----------------------|------------------------------|-------------|
| `prod` (default)     | `api.elections.kalshi.com`   | **YES**     |
| `demo`               | `demo-api.kalshi.co`         | No (paper)  |

### Kalshi Price Fields (CRITICAL)

Kalshi deprecated integer cent fields in favor of `*_dollars` string fields (subpenny pricing migration, Nov 2025). **Always use `*_dollars` fields** (e.g., `yes_bid_dollars`, `yes_ask_dollars`, `last_price_dollars`) - never rely on cent-based fields like `yes_bid`, `yes_ask`, `last_price`. See `docs/_vendor-docs/kalshi-api-reference.md` for details.

### Safe Operations (READ-ONLY)

These commands are safe to run anytime - they only read data:

```bash
uv run kalshi market list              # Public endpoint, no auth needed
uv run kalshi market get TICKER        # Public endpoint, no auth needed
uv run kalshi scan opportunities       # Public endpoint, no auth needed
uv run kalshi portfolio sync           # Authenticated READ from Kalshi API
uv run kalshi portfolio positions      # Reads local DB cache (run sync first!)
uv run kalshi portfolio pnl            # Reads local DB cache
```

**Important:** `portfolio positions` reads from the **local database cache**, not the live API. Always run `portfolio sync` first to pull the latest data from Kalshi.

### Cost-Incurring Operations (USE CAUTION)

These operations may incur real costs:

- **Order placement** (`create_order`) - Real money on prod environment
- **Exa API calls** (`research context`, `research topic`, `research similar`, `research deep`, `research thesis create --with-research`, `research thesis check-invalidation`, `research thesis suggest`, `news collect`) - Exa API usage costs

### Pre-flight Checklist for Authenticated Commands

Before running portfolio or authenticated commands:

1. Read `.env` to confirm `KALSHI_ENVIRONMENT` is set correctly
2. Verify creds for that environment are configured (prod: `KALSHI_KEY_ID` + `KALSHI_PRIVATE_KEY_*`; demo: `KALSHI_DEMO_KEY_ID` + `KALSHI_DEMO_PRIVATE_KEY_*` (falls back to prod vars))
3. Run `uv run kalshi portfolio sync` to populate local DB
4. Then run read commands like `portfolio positions`

## LLM Synthesizer (Agent System)

The agent analysis workflow (`kalshi agent analyze`) uses an LLM to synthesize probability estimates from research.

### Frontier Models (2026)

| Provider | Model | Model ID | Use Case |
|----------|-------|----------|----------|
| **Anthropic** | Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` | Primary synthesizer (SPEC-042) |

Only `claude-sonnet-4-5-20250929` has been validated in this repo. If you change the model ID, verify it works and update
[SPEC-042](docs/_specs/SPEC-042-llm-synthesizer-implementation.md).

### Configuration

```bash
# Set synthesizer backend (default: anthropic)
export KALSHI_SYNTHESIZER_BACKEND=anthropic
export ANTHROPIC_API_KEY=your_key_here

# Run analysis with real LLM
uv run kalshi agent analyze TICKER --mode standard
```

See [SPEC-042](docs/_specs/SPEC-042-llm-synthesizer-implementation.md) for implementation details.

## Documentation Tracking

When you find drift, bugs, or technical debt, record them in the appropriate tracker:

- Active bugs: `docs/_bugs/README.md`
- Active specs: `docs/_specs/README.md`
- Backlog (blocked/deferred): `docs/_future/README.md`
- Technical debt: `docs/_debt/README.md`
