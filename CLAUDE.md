# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
| `kalshi-cli` | `.claude/skills/kalshi-cli/` | CLI commands, database queries, workflows, gotchas |
| `kalshi-codebase` | `.claude/skills/kalshi-codebase/` | Repo navigation and codebase structure |
| `kalshi-ralph-wiggum` | `.claude/skills/kalshi-ralph-wiggum/` | Ralph Wiggum autonomous loop operation |
| `kalshi-doc-audit` | `.claude/skills/kalshi-doc-audit/` | Documentation auditing against SSOT |

Skills are also mirrored to `.codex/skills/` for other agents.

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

### If Pre-commit Fails

1. Review the error output
2. Fix the issues (many auto-fix with `--fix`)
3. Re-run `uv run pre-commit run --all-files`
4. Only commit after ALL checks pass

## Build & Development Commands

```bash
# Install dependencies (use uv, not pip)
uv sync                      # Production deps only
uv sync --all-extras         # All deps including dev and research
uv run pre-commit install    # CRITICAL: Install commit hooks

# Quality gates (all must pass before commits)
uv run ruff check .          # Lint
uv run ruff format .         # Format (or --check to verify)
uv run mypy src/             # Type checking (strict mode)
uv run pytest                # All tests

# Run single test file or specific test
uv run pytest tests/unit/api/test_client.py -v
uv run pytest tests/unit/api/test_client.py::test_name -v

# Test with coverage
uv run pytest --cov=kalshi_research --cov-report=term-missing

# Database migrations
uv run alembic upgrade head              # Run migrations
uv run alembic revision --autogenerate -m "message"  # Create migration

# CLI usage
uv run kalshi --help
uv run kalshi data init
uv run kalshi data sync-markets
uv run kalshi scan opportunities --filter close-race
```

## Code Quality Standards

### FORBIDDEN Patterns

- **NO `# type: ignore`** - Fix the type error properly
- **NO untyped `Any`** - Use specific types (exception: JSON dicts as `dict[str, Any]`)
- **NO `--no-verify` commits** - Always run pre-commit hooks
- **NO manual git commits** - Use `uv run pre-commit run` first

### Database Safety (Do Not Destroy State)

- **NEVER delete `data/kalshi.db`** to "fix" corruption. Diagnose and recover instead:
  - `sqlite3 data/kalshi.db "PRAGMA integrity_check;"`
  - `sqlite3 data/kalshi.db ".recover" | sqlite3 data/recovered.db`
- `data/exa_cache/` is safe to delete; the SQLite DB is not.
- **SQLite concurrency:** Avoid running two write-heavy commands simultaneously (e.g., two `data sync-markets` in parallel). SQLite locks the entire DB on write; concurrent writers will get "database is locked" errors.
- See `.claude/skills/kalshi-cli/GOTCHAS.md` for the full "Critical Anti-Patterns" section.

## Architecture

### Layer Structure

```
src/kalshi_research/
├── api/           # Kalshi API clients (HTTP boundary)
│   ├── client.py  # KalshiPublicClient (no auth), KalshiClient (auth)
│   ├── models/    # Pydantic v2 models (frozen, immutable)
│   └── auth.py    # RSA signing for authenticated endpoints
├── data/          # Persistence layer
│   ├── database.py    # DatabaseManager (async SQLite via aiosqlite)
│   ├── models.py      # SQLAlchemy ORM models
│   ├── repositories/  # Repository pattern (markets, events, prices)
│   ├── fetcher.py     # DataFetcher (coordinates API → DB)
│   └── export.py      # DuckDB/Parquet export
├── exa/           # Exa API client for research
├── news/          # News collection and sentiment analysis
├── analysis/      # Research analytics
│   ├── calibration.py   # Brier scores, calibration curves
│   ├── correlation.py   # Event correlation, arbitrage detection
│   ├── edge.py          # Edge utilities (thesis deltas, etc.)
│   ├── liquidity.py     # Liquidity + orderbook analysis
│   ├── scanner.py       # Market scanner (close races, movers, expiring soon)
│   ├── categories.py    # Category aliases/helpers
│   └── visualization.py # Plotting helpers
├── alerts/        # Alert system
│   ├── conditions.py    # Alert conditions (price, volume, spread, sentiment)
│   ├── monitor.py       # AlertMonitor (async polling)
│   └── notifiers.py     # Console, file, webhook notifiers
├── research/      # Research tools
│   ├── thesis.py        # Thesis tracking
│   ├── backtest.py      # ThesisBacktester
│   └── notebook_utils.py # Jupyter helpers
├── portfolio/     # Portfolio tracking (no order placement)
│   ├── models.py        # Position, Trade models
│   ├── pnl.py           # P&L calculator
│   └── syncer.py        # Sync from Kalshi API
├── execution/     # Execution safety harness (not exposed via CLI today)
│   ├── executor.py
│   ├── models.py
│   └── audit.py
└── cli/           # Typer CLI package (kalshi command)
```

### Key Patterns

**API Clients**: Use async context managers. `KalshiPublicClient` for research (no auth), `KalshiClient` for portfolio sync (requires API key).

**Kalshi Price Fields (CRITICAL)**: Kalshi deprecated integer cent fields in favor of `*_dollars` string fields (subpenny pricing migration, Nov 2025). **Always use `*_dollars` fields** (e.g., `yes_bid_dollars`, `yes_ask_dollars`, `last_price_dollars`) - never rely on cent-based fields like `yes_bid`, `yes_ask`, `last_price`. See `docs/_vendor-docs/kalshi-api-reference.md` for details.

**Exa deep research**: `/research/v1` runs asynchronously; use `ExaClient.list_research_tasks()` / `find_recent_research_task()` to recover results after crashes.

**Repository Pattern**: Prefer repositories in `data/repositories/` for shared persistence logic. For
small, one-off queries in CLI commands, direct `select()` usage is acceptable when it avoids unnecessary abstraction,
but don't duplicate repository behavior in multiple places.

**Pydantic Models**: API models in `api/models/` are frozen (`model_config = ConfigDict(frozen=True)`). Don't mutate them.

**SQLAlchemy Models**: ORM models in `data/models.py` use SQLAlchemy 2.0 declarative style with `Mapped[]` type hints.

**Testing Philosophy**: Only mock at system boundaries (HTTP via `respx`, filesystem via `tmp_path`). Use real Pydantic models, real in-memory SQLite for repositories.

## CLI Structure

```
kalshi
├── version, status
├── data        # init, migrate, sync-markets, sync-settlements, sync-trades, snapshot, collect, export, stats, prune, vacuum
├── market      # list, get, orderbook, liquidity, history
├── scan        # opportunities, movers, arbitrage
├── alerts      # list, add, remove, monitor, trim-log
├── analysis    # metrics, calibration, correlation
├── research    # backtest, context, topic, similar, deep, thesis, cache
│   ├── thesis  # create, list, show, resolve, check-invalidation, suggest
│   └── cache   # clear
├── news        # track, untrack, list-tracked, collect, sentiment
└── portfolio   # balance, sync, positions, pnl, history, link, suggest-links
```

## Test Organization

Tests mirror source structure: `tests/unit/api/`, `tests/unit/data/`, etc. Integration tests live in `tests/integration/` (live API tests are opt-in via env vars).

Fixtures in `conftest.py` provide `make_market`, `make_orderbook`, `make_trade` factories that return dicts matching API response structure.

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

## Ralph Wiggum Loop (Optional)

- State files: `PROGRESS.md`, `PROMPT.md`
- Operator script: `./scripts/ralph-loop.sh start` (default tmux session: `kalshi-ralph`; override via `RALPH_TMUX_SESSION=...`)
- Reference: `docs/_ralph-wiggum/protocol.md`
